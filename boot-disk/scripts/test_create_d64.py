#!/usr/bin/env python3
"""Check create_d64's output against the public disk format, by reading the bytes back."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from create_d64 import D64, build, sectors_on_track  # noqa: E402

SCRIPT = Path(__file__).resolve().parent / "create_d64.py"
HEADER_OFFSET = 0x16500
FREE_BLOCKS = 664  # 683 sectors, less track 18's 19
BLOCK_DATA = 254


def offset(track: int, sector: int) -> int:
    return (sum(sectors_on_track(t) for t in range(1, track)) + sector) * 256


def read_chain(image: bytes, track: int, sector: int) -> bytes:
    out = bytearray()
    for _ in range(683):
        block = image[offset(track, sector) : offset(track, sector) + 256]
        if block[0] == 0:
            return bytes(out + block[2 : block[1] + 1])
        out += block[2:]
        track, sector = block[0], block[1]
    raise AssertionError("the chain never ended")


def chain_sectors(image: bytes, track: int, sector: int) -> list[tuple[int, int]]:
    out = []
    while True:
        out.append((track, sector))
        block = image[offset(track, sector) : offset(track, sector) + 256]
        if block[0] == 0:
            return out
        if len(out) > 683:
            raise AssertionError("the chain never ended")
        track, sector = block[0], block[1]


def directory(image: bytes) -> list[tuple[int, bytes]]:
    """Each entry, in directory order: its type byte and its name."""
    out = []
    for track, sector in chain_sectors(image, 18, 1):
        block = image[offset(track, sector) : offset(track, sector) + 256]
        for at in range(0, 256, 32):
            if block[at + 2]:
                out.append((block[at + 2], block[at + 5 : at + 21].rstrip(b"\xa0")))
    return out


class CreateD64Test(unittest.TestCase):
    def test_blank_disk_has_664_blocks_free_and_a_named_header(self) -> None:
        image = D64("HELLO WORLD", "AB").image()
        self.assertEqual(len(image), 174848)
        header = image[HEADER_OFFSET : HEADER_OFFSET + 256]
        self.assertEqual(header[0:3], bytes([18, 1, ord("A")]))
        self.assertEqual(header[0x90:0xA0], b"HELLO WORLD" + bytes([0xA0]) * 5)
        self.assertEqual(header[0xA2:0xA7], b"AB\xa02A")
        free = sum(header[4 + (t - 1) * 4] for t in range(1, 36) if t != 18)
        self.assertEqual(free, 664)

    def test_each_file_size_reads_back_through_its_chain(self) -> None:
        for size in (1, 253, 254, 255, 508, 5000, 39761):
            with self.subTest(size=size):
                disk = D64("D", "ID")
                payload = bytes((i * 7 + 1) & 0xFF for i in range(size))
                disk.add_file("FILE", payload)
                image = disk.image()
                entry = image[offset(18, 1) : offset(18, 1) + 32]
                self.assertEqual(entry[2], 0x82)
                self.assertEqual(read_chain(image, entry[3], entry[4]), payload)
                self.assertEqual(entry[30] | entry[31] << 8, (size + 253) // 254)

    def test_bam_counts_what_the_files_used(self) -> None:
        disk = D64("D", "ID")
        disk.add_file("FILE", bytes(5000))
        image = disk.image()
        header = image[HEADER_OFFSET : HEADER_OFFSET + 256]
        free = sum(header[4 + (t - 1) * 4] for t in range(1, 36) if t != 18)
        self.assertEqual(free, 664 - 20)

    def test_directory_continues_into_another_sector_after_eight_files(self) -> None:
        disk = D64("D", "ID")
        for number in range(9):
            disk.add_file(f"F{number}", bytes([number]))
        image = disk.image()
        first = image[offset(18, 1) : offset(18, 1) + 256]
        self.assertEqual(first[0], 18)
        second = image[offset(18, first[1]) : offset(18, first[1]) + 256]
        self.assertEqual(second[0:2], bytes([0, 0xFF]))
        self.assertEqual(second[5:7], b"F8")

    def test_names_become_capitals_and_are_bounded(self) -> None:
        disk = D64("D", "ID")
        disk.add_file("config", b"x")
        image = disk.image()
        self.assertEqual(image[offset(18, 1) + 5 : offset(18, 1) + 11], b"CONFIG")
        with self.assertRaises(ValueError):
            disk.add_file("A" * 17, b"x")
        with self.assertRaises(ValueError):
            disk.add_file("", b"x")
        with self.assertRaises(ValueError):
            disk.add_file("EMPTY", b"")

    def test_a_name_goes_on_the_disk_once(self) -> None:
        disk = D64("D", "ID")
        disk.add_file("CONFIG", b"x")
        for again in ("CONFIG", "config"):
            with self.subTest(name=again), self.assertRaisesRegex(ValueError, "already on the disk"):
                disk.add_file(again, b"y")

    def test_a_full_disk_holds_664_blocks_and_not_a_byte_more(self) -> None:
        disk = D64("D", "ID")
        disk.add_file("BIG", bytes(FREE_BLOCKS * BLOCK_DATA))
        with self.assertRaisesRegex(ValueError, "disk full"):
            disk.add_file("MORE", b"x")
        with self.assertRaisesRegex(ValueError, "disk full"):
            D64("D", "ID").add_file("BIG", bytes(FREE_BLOCKS * BLOCK_DATA + 1))

    def test_file_data_never_goes_on_the_directory_track(self) -> None:
        disk = D64("D", "ID")
        payload = bytes((i * 13 + 5) & 0xFF for i in range(FREE_BLOCKS * BLOCK_DATA))
        disk.add_file("BIG", payload)
        image = disk.image()
        entry = image[offset(18, 1) : offset(18, 1) + 32]
        sectors = chain_sectors(image, entry[3], entry[4])
        self.assertEqual(len(set(sectors)), FREE_BLOCKS)
        self.assertNotIn(18, {track for track, _ in sectors})
        self.assertEqual(read_chain(image, entry[3], entry[4]), payload)
        header = image[HEADER_OFFSET : HEADER_OFFSET + 256]
        self.assertEqual(header[4 + 17 * 4], 17)  # track 18: only the BAM and one directory sector used
        self.assertEqual(sum(header[4 + (t - 1) * 4] for t in range(1, 36) if t != 18), 0)

    def test_the_directory_holds_144_files(self) -> None:
        disk = D64("D", "ID")
        for number in range(144):
            disk.add_file(f"F{number}", b"x")
        self.assertEqual(directory(disk.image())[-1], (0x82, b"F143"))
        with self.assertRaisesRegex(ValueError, "directory full"):
            disk.add_file("ONE MORE", b"x")


class BuildTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.input = Path(tmp.name) / "in"
        self.input.mkdir()
        self.output = Path(tmp.name) / "out" / "disk.d64"

    def write(self, *names: str) -> None:
        for name in names:
            (self.input / name).write_bytes(name.encode())

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), "-i", str(self.input), "-o", str(self.output), *args],
                              capture_output=True, text=True, check=False)

    def test_a_seq_suffix_makes_a_seq_entry(self) -> None:
        self.write("NOTES.seq", "PROG.prg")
        image = build(self.input, ["NOTES.seq", "PROG.prg"], "D", "ID")
        self.assertEqual(directory(image), [(0x81, b"NOTES"), (0x82, b"PROG")])

    def test_files_go_on_the_disk_in_the_order_given(self) -> None:
        # LOAD"*",8 loads the first entry: the boot disk puts CONFIG there.
        self.write("ABC.prg", "CONFIG.prg", "FUJIDEMO.prg")
        image = build(self.input, ["CONFIG.prg", "FUJIDEMO.prg", "ABC.prg"], "D", "ID")
        self.assertEqual([name for _, name in directory(image)], [b"CONFIG", b"FUJIDEMO", b"ABC"])

    def test_cli_writes_the_disk_in_the_order_given(self) -> None:
        self.write("A.prg", "B.prg")
        result = self.run_cli("--files", "B.prg", "A.prg")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f"{self.output}: 2 file(s)")
        self.assertEqual([name for _, name in directory(self.output.read_bytes())], [b"B", b"A"])

    def test_cli_sorts_by_name_without_files(self) -> None:
        self.write("B.prg", "A.prg")
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([name for _, name in directory(self.output.read_bytes())], [b"A", b"B"])

    def test_cli_reports_an_error_and_writes_nothing(self) -> None:
        self.write("A.prg", "a.seq")
        for files, message in ((["MISSING.prg"], "MISSING.prg"), (["A.prg", "a.seq"], "already on the disk")):
            with self.subTest(files=files):
                result = self.run_cli("--files", *files)
                self.assertEqual(result.returncode, 1)
                self.assertTrue(result.stderr.startswith("create_d64: "), result.stderr)
                self.assertIn(message, result.stderr)
                self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
