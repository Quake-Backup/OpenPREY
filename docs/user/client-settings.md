# Client Settings Guide

> [!NOTE]
> Inherited from openQ4 and not yet checked against PREY. This page describes what the engine code does; PREY behavior stays validation-pending until the [rebase status ledger](../dev/prey-rebase/status-ledger.md) records evidence for it.

This guide helps you find the most useful openPR06 settings without digging through every advanced option.

## In-Game Menus

openPR06 draws PREY's menus with its retained interface (`ui_retained 1`, the default): the same screens and layout as PREY's own, as vectors that stay sharp at any resolution, with keyboard and controller navigation. `ui_retained 0` brings back PREY's stock menus, which have the same pages with a few openPR06 additions:

- **Options -> Controls**: key bindings for movement, combat, weapons, look, other actions and multiplayer, plus control profiles.
- **Options -> Game Options**: decals, HUD, weapon visibility, subtitles, profanity filter, crosshair, dynamic difficulty, and mouse settings.
- **Options -> Video**: resolution, fullscreen, brightness, gamma, quality presets and advanced rendering options, plus openPR06's **Post FX** and **Advanced FX** tabs for MSAA, post anti-aliasing, SSAO, bloom, HDR tone mapping and the CRT filter.
- **Options -> Audio**: volume, music, speakers, output device and EAX reverb.

The retained interface's Options page holds more: Mouse and Controller tabs, and HUD, Accessibility and System tabs under Game Options. Everything else is a console setting.

Besides PREY's own menu sounds, the retained interface plays two quiet cues: a soft tick when you move between controls with the mouse, keys or a controller, and a softer click when a setting changes without a sound of its own. Set `ui_retainedCueSounds 0` to turn them off and keep only PREY's sounds.

## Recommended First Checks

- Pick fullscreen or windowed mode, and borderless if you play windowed.
- Choose **Recommended** on the first **Options -> Video** tab, or run `autoDetectPerformancePreset`, if this is a new machine or you're near the [minimum requirements](getting-started.md#system-requirements).
- Adjust mouse sensitivity, or set up a controller from the console.
- Confirm your display target with `listDisplays` and `r_screen` if you use multiple monitors.
- Decide whether you want extra effects such as bloom or shadow mapping.
- Set music volume to taste.

## Which Guide Covers What?

- [Display Settings](display-settings.md): renderer, presets, resolution, fullscreen, windowed mode, multi-monitor, anti-aliasing and aspect behavior
- [Input Settings](input-settings.md): key binds, mouse tuning, controller support and config files
- [Gameplay Settings](gameplay-settings.md): PREY's game options and audio settings
- [Shadow Mapping](shadow-mapping.md): optional shadow-map tuning
- [Cel Shading](cel-shading.md): banded lighting and outline settings for the cel-shaded look
- [DDS Texture Replacements](texture-replacements.md): DXT/BC7 texture-pack layout and diagnostics
- [Steam Deck](steam-deck.md): launcher and handheld-specific notes

For console-level configuration and file layout, see [TECHNICAL.md](../../TECHNICAL.md).
