# Menu transitions, a sixth retained UI round

A sixth round on 22 November 2026 measured openPR06's retained menus while
their pages open and close: a full page (Options, Load Game, Save Game,
MultiPrey, Credits) widens out of the title's bottom bar for 200 ms and rises
to the full frame for 500 ms, and shrinks back the same way (section 8 of the
[Prey visual specification](../prey-ui-visual-design.md#8-motion-and-sound)).
Opening Options felt laggy. It follows the [event costs](event-costs.md)
round of 21 November, which measured pages at rest and the events that
change them.

## What a transition cost

`openq4-retained-ui-benchmark --transition <document> <enter> <leave>
[cycles] [frames]` is new: it plays a page's opening event (`onActivate`) and
its `pageLeave`, each followed by 45 frames at 60 Hz, for several cycles, and
reports the frames that animate. In the engine, `profileFrameWork` and
`ui_retainedProfile` measured the same openings from the title
(`.tmp/menu-perf/`, below).

- **Options cost 9 to 18 ms of CPU a frame for the whole 700 ms**, against
  0.06 ms for the title at rest; MultiPrey 2 to 3 ms, Load Game, Save Game
  and Credits under 1 ms. In the engine, Options' frames ran 12 to 60 ms
  (p95 19.6 ms) where the title ran 5 ms, so at 60 Hz the opening dropped
  frames every time, and twice as many the first time.
- **The frame's size animated, and a size change lays out the whole
  document.** The page's `width` and `height` were timeline tracks. RmlUi 6.3
  formats a document from its root whenever any box's size changes, so each
  frame laid out all of Options' 8,800 nodes (6.2 ms of the 10.7 ms the
  engine profiled), though nothing inside the frame moved relative to it.
- **Every closed list on the page repainted every moving frame.** A settled
  closed choice skips its repaint only within one presentation pass, and any
  animated property started a new pass; Options has 86 lists. This was the
  largest single cost in the benchmark (37% of a frame).
- **The focused control's reveal ran every moving frame.** The runtime
  decides a focused control has reflowed when any ancestor's offset or size
  changes, and the page's own box was one of them; each reveal brought the
  styles up to date again (8% of a frame), to scroll nothing.
- **Moving artwork recompiled whenever the clip edge crossed it.** A vector's
  compilation is keyed on the visible region in 256-pixel steps, and that
  region grows with the frame, so each row plate, tab and title bar compiled
  again whenever the frame's edge crossed a step, and the change also
  discarded the sub-pixel phases it had cached while sliding (13 paths a
  frame on Options, 8 on MultiPrey).
- **MultiPrey's first opening parsed its 3.5 MB document in the frame that
  opened it** (174 ms): the title prefetched only Options and Quake 4's
  Single Player page, so the page warm-up never reached MultiPrey.

## What changed

- **A full page's frame no longer changes size**
  (`full_page`, `tools/ui/build_retained_screens.py`). Two fixed boxes 1,000 u
  square clip the page instead: `page` stands at the frame's top-left corner
  and `page-clip` inside it puts its own bottom-right corner on the frame's.
  The frame's parts and contents hang from the corner they follow, and its
  body and rails are fixed-length strips revealed by a clip of their own. The
  timelines move these boxes (`left` and `top` only), which RmlUi places
  without a layout. At rest `page-contents` covers the frame exactly, so the
  lists' popups now place within `page-contents`. The five full pages are
  regenerated; captures of Options, Load Game and MultiPrey growing, at rest
  and shrinking match the previous pages.
- **`clip` is an authorable property** (`auto`, `none` or `always`;
  [document format](document-format.md)). A hidden overflow clips only what
  the last layout found past the box's far edges, and the frame's boxes move
  their content by offsets alone, so they set `always`.
- **A closed list repaints only when a pass can undo its paint**
  (`ValueControlView::PaintsNode`, `Runtime.cpp`): a complete pass, or one
  that writes its value text, its popup's subtree, or the opacity of an
  ancestor its popup's filter reads. A frame growing, or any decoration
  moving, leaves the lists as painted.
- **The focus reflow check stops at the outermost scrolling ancestor**
  (`FocusLayout`). A reveal scrolls only those, measuring the control in each
  one's plane, so movement above them changes nothing it would do.
- **Artwork wholly inside the visible region keys its compilation on its own
  extent** (`ArtworkExtent`, `VectorElement.cpp`): its control points, widened
  by its stroke's furthest join or cap and a pixel each side. The mesh is the
  same whatever region bounds it, and the key no longer changes as the clip
  grows. A sliding element whose region changes is still moving, so it keeps
  its cached phases; one that stays put under a changing clip compiles
  exactly, as before.
- **The title prefetches MultiPrey** (`PrefetchRetainedNextPages`): its parse
  runs on the job workers while the title shows, and the warm-up builds its
  view (41 ms) and compiles its artwork while the title rests.

Behaviour is unchanged: the same frames, the same clip, the same focus and
popups. A static element under a moving clip and anything partly clipped
compile as before.

## Results

Best of three interleaved benchmark runs (`ab.py`, debugoptimized
`builddir-perf`, a machine shared with other sessions), median of the
animating frames:

| Page | Opening, before | Engine changes only | Now | Leaving, before | Now | Paths compiled a frame |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Options | 9.01 ms | 2.51 ms | 1.49 ms | 8.87 ms | 1.49 ms | 13 -> 0 |
| MultiPrey | 2.09 ms | 1.09 ms | 0.86 ms | 2.04 ms | 0.75 ms | 8 -> 0 |
| Load Game | 0.73 ms | 0.46 ms | 0.41 ms | 0.69 ms | 0.28 ms | 4 -> 0 |
| Save Game | 0.75 ms | 0.44 ms | 0.38 ms | 0.70 ms | 0.28 ms | 4 -> 0 |
| Credits | 0.99 ms | 0.90 ms | 0.40 ms | 1.00 ms | 0.33 ms | 1 -> 0 |

Options' p95 fell from 13.5 to 2.7 ms and its layout from 6.7 to 0.8 ms.
The first frame of an opening (`--screen`) fell from 9 to 11 ms to 3.6 ms;
loading the documents costs the same (Options' parse 122 ms, view 160 ms on
the workers and while the title rests), and a page at rest 0.07 to 0.09 ms.

In the engine (`ui_retainedProfile 60` over Options' opening, OpenGL,
1280x720 window): retained CPU p50 10.7 to 3.5 ms, p95 17.1 to 6.2 ms, layout
6.2 to 1.8 ms, paths compiled 24 to 2.6 a frame. Whole frames
(`profileFrameWork`, uncapped): Options' opening p95 19.6 to 9.0 ms, opening
it again 17.4 to 8.5 ms, MultiPrey 13.5 to 6.0 ms; at a 60 Hz cap no
profiled frame of Options' or MultiPrey's opening passed 17.7 ms.

## Found, not fixed

- **The click frame still does the page's setup.** The first MultiPrey click
  takes about 40 ms: it opens the network port, starts the server scan and
  parses the player models' declarations (`PublishRetainedMultiPrey`,
  `Session_ScanPlayerModels`). Opening them earlier would open a socket, and
  possibly a firewall prompt, before the player asks for multiplayer. Options'
  first click publishes its controls, video modes and sound devices (18 ms
  of commands, then a 23 ms first frame; 5 ms of commands on later opens).
- **Loading a page ahead is one frame of the title's rest:** Options' view
  build is about 150 ms on this machine, in one frame, and shows as a stall
  if the title is animating then.
- **A moving page still renders all of itself and refreshes input
  eligibility every frame** (about 1.5 ms on Options): its content moves, so
  frame replay cannot serve it.
- `openq4-ui-value-runtime` and `openq4-ui-choice-scroll-runtime` fail "an
  open list keeps the full pass every frame" with or without this round's
  engine changes.

## Evidence, 22 November 2026

The kit is in `.tmp/menu-perf/`: `run.ps1` (a windowed run from a build
directory with a cfg as the save path's `autoexec.cfg`, so the title opens
with its entrance; `-Sample` records `tools/debug/cpu_sampler.py` stacks),
`pages2.cfg` (each page opened and closed under `profileFrameWork`, the
capture starting a frame before the click), `loop.cfg` (Options and
MultiPrey with `ui_retainedProfile`), `shots.cfg` (captures during growth, at
rest and while leaving), `ab.py` (the benchmark A/B), `window.py` (sample
shares over chosen frames) and the comparison sheets and results in `out/`.
The baseline benchmark was built from HEAD's copies of the five changed
engine files; the previous documents come from `git show HEAD:`.
