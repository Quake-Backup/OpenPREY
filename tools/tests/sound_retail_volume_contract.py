#!/usr/bin/env python3
"""Pin retail Prey's volume routing and voice ducking (docs/dev/audio-modernization.md).

Retail PREY.exe 1.4 scales an SC_MUSIC sound by s_musicVolume_dB in place of s_volume_dB, every
other sound by s_volume_dB alone, applies no Quake 4 speaker fraction, and ducks the normal and
spirit-walk classes while a ducking dialogue line plays.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8", errors="replace")


def body(text: str, signature: str) -> str:
    at = text.index(signature)
    start = text.index("{", at)
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[at:index + 1]
    raise ValueError(signature)


def cvar_default(text: str, name: str) -> str:
    match = re.search(r'idCVar\s+\w+\(\s*"' + re.escape(name) + r'",\s*"([^"]*)"', text)
    return match.group(1) if match else None


def main() -> int:
    failures = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    emitter = read("src/sound/snd_emitter.cpp")
    system = read("src/sound/snd_system.cpp")
    world = read("src/sound/snd_world.cpp")
    common = read("src/framework/Common.cpp")
    local = read("src/sound/snd_local.h")

    update = body(emitter, "void idSoundChannel::UpdateVolume( int currentTime )")
    music = update.index("if( SoundIsMusicClass( parms ) )")
    branch = update[music:update.index("if( !SoundUsesMusicVolume( parms ) )", music)]
    require("s_musicVolume" in branch and "s_volume" in branch.split("else", 1)[1],
            "music class takes the music volume, everything else the master volume")
    require("s_musicVolume" not in branch.split("else", 1)[1], "the music volume reaches only SC_MUSIC")
    require(update.count("s_volume.GetFloat()") == 1, "the master volume is applied once, outside the music branch")
    require("return parms.soundClass == SOUND_CLASS_MUSICAL;" in body(emitter, "static bool SoundIsMusicClass("),
            "the music volume follows the sound class, not the sample path")
    for name in ("s_speakerFraction", "s_radioChatterFraction"):
        require(name + ".Get" not in emitter and 'idCVar ' + name not in system,
                f"{name} is Quake 4 only and must not attenuate Prey sounds")

    gain = body(system, "float idSoundSystemLocal::LoadingMusicGain() const")
    require("soundClass == SOUND_CLASS_MUSICAL" in gain and "s_musicVolume" in gain and "s_volume" in gain,
            "load music follows the same music/master split")
    require(gain.count("gain * volume") == 1, "load music applies one volume, not both")

    require(cvar_default(world, "s_volume_dB") == "0", "s_volume_dB defaults to retail's 0 dB")
    require(cvar_default(common, "s_musicvolume_dB") == "0", "s_musicvolume_dB defaults to retail's 0 dB")
    require(cvar_default(system, "s_volume") == "1" and cvar_default(system, "s_musicVolume") == "1",
            "the linear aliases default to unity")
    for name, value in (("s_voiceDucking", "1"), ("s_voiceDuckVolume", "-4.5"),
                        ("s_voiceDuckFadeTimeOut", "0.2"), ("s_voiceDuckFadeTimeIn", "0.5")):
        require(cvar_default(world, name) == value, f"{name} defaults to retail's {value}")

    require("virtual void			SetVoiceDucker( bool active );" in local, "idSoundWorldLocal overrides SetVoiceDucker")
    ducker = body(world, "void idSoundWorldLocal::SetVoiceDucker( bool active )")
    require("FadeSoundClasses( SOUNDCLASS_NORMAL, to, over );" in ducker and
            "FadeSoundClasses( SOUNDCLASS_SPIRITWALK, to, over );" in ducker,
            "ducking fades the normal and spirit-walk classes")
    require("SOUNDCLASS_MUSIC" not in ducker and "SOUNDCLASS_VOICE" not in ducker.replace("SOUNDCLASS_VOICEDUCKER", ""),
            "ducking leaves voice and music alone")
    require("s_voiceDuckVolume" in ducker and "s_voiceDuckFadeTimeOut" in ducker and "s_voiceDuckFadeTimeIn" in ducker,
            "ducking uses the retail cvars")

    start = body(emitter, "int idSoundEmitterLocal::StartSound(")
    require("chanParms.soundClass == SOUNDCLASS_VOICEDUCKER" in start and "SetVoiceDucker( true )" in start,
            "a ducking line ducks the mix as it starts")
    completion = body(emitter, "bool idSoundEmitterLocal::CheckForCompletion( int currentTime )")
    require("SOUNDCLASS_VOICEDUCKER" in completion and "SetVoiceDucker( false )" in completion,
            "a ducking line lifts the duck as it completes")
    require("SetVoiceDucker" not in body(emitter, "void idSoundEmitterLocal::StopSound( const s_channelType channel )"),
            "retail's StopSound leaves the duck in place")

    if failures:
        for failure in failures:
            print("FAIL:", failure)
        return 1
    print("sound retail volume contract: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
