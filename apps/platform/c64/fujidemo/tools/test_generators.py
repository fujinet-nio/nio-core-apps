#!/usr/bin/env python3
# Copyright (C) 2026 Andrew Diller
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that gen_gfx.py and gen_music.py write includes that fit the demo and its player.

    python3 -m unittest discover -s apps/platform/c64/fujidemo/tools -p 'test_*.py'
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import gen_gfx  # noqa: E402
import gen_music  # noqa: E402

SPRITE_BYTES = 64
SPRITE_AREA = 0x400  # SPR in src/c64.cfg: $3400-$37ff


def run_generator(script: str) -> tuple[dict[str, int], dict[str, list[int]]]:
    """Run a generator, then read back its constants and the bytes under each label."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out.inc"
        result = subprocess.run([sys.executable, str(TOOLS / script), str(out)],
                                capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise AssertionError(f"{script} failed:\n{result.stderr}")
        text = out.read_text()
    constants: dict[str, int] = {}
    tables: dict[str, list[int]] = {}
    label = None
    for line in text.splitlines():
        if match := re.fullmatch(r"(\w+) = \$?(\w+)", line):
            constants[match[1]] = int(match[2], 16 if "$" in line else 10)
        elif match := re.fullmatch(r"(\w+):", line):
            label = match[1]
            tables[label] = []
        elif line.strip().startswith(".byte $") and label:
            tables[label] += [int(value.strip().lstrip("$"), 16) for value in line.split(".byte", 1)[1].split(",")]
    return constants, tables


class GenGfxTest(unittest.TestCase):
    def test_it_writes_the_logo_sprites_and_tables(self) -> None:
        constants, tables = run_generator("gen_gfx.py")
        self.assertEqual(constants["NUM_SHAPES"], 15)
        self.assertEqual(len(tables["sprite_data"]), 15 * SPRITE_BYTES)
        self.assertEqual(len(tables["logo_chars"]), 8 * constants["LOGO_NUM_CHARS"])
        self.assertEqual(len(tables["logo_map"]), 40 * gen_gfx.LOGO_ROWS)
        for name in ("orbit_x_lo", "orbit_x_hi", "orbit_y", "wave_y", "sway_x", "bar_y", "filter_sweep"):
            with self.subTest(table=name):
                self.assertEqual(len(tables[name]), 256)

    def test_the_logo_fits_in_its_characters(self) -> None:
        # Screen codes 64-223 hold the logo; 224-255 are the starfield and the lines.
        tiles, screen = gen_gfx.logo()
        self.assertLessEqual(gen_gfx.LOGO_FIRST_CHAR + len(tiles) - 1, gen_gfx.LOGO_LAST_CHAR)
        drawn = {code for code in screen if code != 32}
        self.assertEqual(drawn, set(range(gen_gfx.LOGO_FIRST_CHAR, gen_gfx.LOGO_FIRST_CHAR + len(tiles))))

    def test_fifteen_sprite_shapes_of_64_bytes(self) -> None:
        shapes = gen_gfx.sprite_shapes()
        self.assertEqual(len(shapes), 15)
        self.assertLessEqual(len(shapes) * SPRITE_BYTES, SPRITE_AREA)
        for number, shape in enumerate(shapes):
            with self.subTest(shape=number):
                self.assertEqual(len(gen_gfx.sprite_bytes(shape)), SPRITE_BYTES)


class GenMusicTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.patterns, cls.orders = gen_music.patterns_and_orders()

    def test_it_writes_the_song(self) -> None:
        constants, tables = run_generator("gen_music.py")
        self.assertEqual(constants["SONG_BARS"], len(gen_music.SONG))
        self.assertEqual(constants["SPEED"], gen_music.SPEED)
        for voice in (1, 2, 3):
            with self.subTest(voice=voice):
                self.assertEqual(tables[f"order{voice}"][-2:], [0xFF, gen_music.LOOP_BAR])
        for number in range(len(self.patterns)):
            self.assertEqual(tables[f"pat{number}"], list(self.patterns[number]))
        for name in ("freq_pal_lo", "freq_pal_hi", "freq_ntsc_lo", "freq_ntsc_hi", "vib_lo", "vib_hi"):
            with self.subTest(table=name):
                self.assertEqual(len(tables[name]), 96)

    def test_the_tables_stay_within_the_players_limits(self) -> None:
        self.assertLessEqual(len(gen_music.INSTRUMENTS), 16)  # set with $60-$6f
        self.assertLess(len(self.patterns), 0xFF)  # $ff ends an order list
        self.assertLessEqual(len(gen_music.WAVETABLE), 256)  # indexed with one byte
        for order in self.orders:
            self.assertEqual(len(order), len(gen_music.SONG))
            self.assertLessEqual(len(order) + 2, 256)  # indexed with one byte, then $ff and the loop
        self.assertLess(gen_music.LOOP_BAR, len(gen_music.SONG))
        self.assertGreaterEqual(gen_music.SPEED, 3)  # the hard restart is two frames before a row

    def test_every_pattern_is_one_bar_that_stands_alone(self) -> None:
        # A pattern can follow any other, so it sets its own instrument and length before it plays.
        for number, pattern in enumerate(self.patterns):
            with self.subTest(pattern=number):
                self.assertEqual(pattern[-1], 0xFF)
                rows, length, instrument = 0, None, None
                for byte in pattern[:-1]:
                    if byte < 0x60:
                        self.assertIsNotNone(instrument)
                        self.assertIsNotNone(length)
                        rows += length
                    elif byte < 0x70:
                        instrument = byte & 0x0F
                        self.assertLess(instrument, len(gen_music.INSTRUMENTS))
                    elif 0x80 <= byte < 0xC0:
                        length = (byte & 0x3F) + 1
                    elif byte == 0xC0:
                        self.assertIsNotNone(length)
                        rows += length
                    else:
                        self.fail(f"${byte:02x} means nothing to the player")
                self.assertEqual(rows, 16)

    def test_each_wavetable_program_loops_inside_itself(self) -> None:
        starts = sorted(instrument["wt"] for instrument in gen_music.INSTRUMENTS.values())
        for start, end in zip(starts, starts[1:] + [len(gen_music.WAVETABLE)]):
            with self.subTest(start=start):
                program = gen_music.WAVETABLE[start:end]
                wave, target = program[-1]
                # It ends in a jump, so the player never runs into the next program, and the
                # player follows one jump, so it lands on a step that isn't one.
                self.assertEqual(wave, 0xFF)
                self.assertTrue(start <= target < end - 1, target)
                for wave, note in program[:-1]:
                    self.assertNotEqual(wave, 0xFF)
                    if note & 0x80:
                        self.assertLess(note & 0x7F, 96)  # an absolute note in the frequency table


if __name__ == "__main__":
    unittest.main()
