# FujiNet demo for the C64

A demo of a C64 with FujiNet NIO. It's on the C64 boot disk, and F5 in CONFIG runs it, or
type `LOAD"FUJIDEMO",8` and `RUN`. It runs in a loop:

- A striped FUJINET logo with rainbow colours flowing through it.
- Sprites in two formations that take turns: the letters F-U-J-I-N-E-T and a Wi-Fi icon
  swaying as a sine wave, then eight icons on a drifting Lissajous curve.
- A three-speed parallax starfield.
- Colour bars on sine paths in the top border, and in the lower border one band per SID
  voice that lights up with its notes (PAL only).
- A smooth scroller between two rainbow lines.
- Live date and time from FujiNet. It shows "NO FUJINET FOUND" and keeps running when no
  FujiNet answers.
- "Pocket Packets", a three-voice SID tune of about 60 seconds by Andrew Diller, looping.

Andrew Diller wrote it for [PocketFujiC64](https://github.com/dillera/pocketFujiC64), where
it builds as `PFDEMO.PRG` and reads the clock from the classic FujiNet firmware. This is that
source, carried over: `src/fujidemo.s` is PocketFujiC64's `demo/src/pfdemo.s`, changed to read
the clock over NIO's packet channel, so it needs NIO to show the time, and to describe NIO in
its text. The player and the generators are the same. It runs on PAL and NTSC machines.

## Building

`make TARGET=c64` builds it into `build/c64/bin/fujidemo.prg`, and `make TARGET=c64
boot-disk` also puts it on the disk. It needs Python and cc65's `ca65` and `ld65`, and nothing
from `fujinet-nio-lib`. `make test-c64` runs the generators' tests with the boot disk's.

| File | What |
|---|---|
| `src/fujidemo.s` | Effects, raster interrupts, FujiNet clock, text |
| `src/player.s` | The SID player (order lists, wavetables, hard restart, vibrato, PWM, filter) |
| `src/c64.cfg` | ld65 layout: PRG `$0801-$37ff`, variables at `$c000` |
| `tools/gen_gfx.py` | Art to logo characters, sprites, motion and colour tables |
| `tools/gen_music.py` | The tune, written as Python data, to player tables |
| `tools/test_generators.py` | What the generators write fits the demo and the player |
| `tools/render_art.py` | Draws `art/*.txt` (see below); not part of the build |
| `art/*.txt` | The logo, letters and icons as editable ASCII art |

## Notes

- The raster interrupts go through the KERNAL's `$0314` vector. The KERNAL stays banked in
  because the clock uses the KERNAL's serial calls, from the main loop and never from an
  interrupt.
- A talk to a device that isn't there can hang the KERNAL if a disk drive is on the bus,
  because the drive acknowledges every ATN address. So the clock sends its packet first, which
  sets `ST` bit 7 if nothing took it, and doesn't talk after that.
- Copying the sprite registers takes about 7 raster lines, so the top interrupt fires at line
  2 and the bar loop waits for line 15 or later.
- ca65's `.charmap` maps character constants too: write `$41 + I`, not `'A' + I`.

## The art

`art/*.txt` is what the build reads, and can be edited by hand. `tools/render_art.py` draws
it: the logo and the letter sprites from the [Figtree](https://github.com/erikdkennedy/figtree)
font (Black Italic and Black), and the icons from plain shapes. It needs Pillow, and downloads
the two font files, pinned to a commit and checked by SHA-256, into `build/fonts`:

    python3 apps/platform/c64/fujidemo/tools/render_art.py --preview build/art.png

Figtree is under the SIL Open Font License 1.1, which leaves what is drawn with it free of
the font's licence, so the art is covered by this repository's like the rest of the demo.

## Copyright and licence

Copyright (C) 2026 Andrew Diller. The demo's code, its generators and the music are
contributed under this repository's licence, GPL-3.0-or-later, as each source file says.
