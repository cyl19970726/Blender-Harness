import base64
import binascii
import struct
import tempfile
import unittest
from pathlib import Path

from blender_harness.io import ContractError
from blender_harness.media import inspect_png


VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class MediaTest(unittest.TestCase):
    def test_real_png_is_inspected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "one.png"
            path.write_bytes(VALID_PNG)
            result = inspect_png(path)
            self.assertEqual((result["width"], result["height"]), (1, 1))
            self.assertEqual(len(result["sha256"]), 64)

    def test_ascii_file_disguised_as_png_is_contract_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fake.png"
            path.write_text("placeholder\n", encoding="utf-8")
            with self.assertRaises(ContractError):
                inspect_png(path)

    def test_corrupt_idat_stream_is_contract_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corrupt.png"
            data = bytearray(VALID_PNG)
            idat = data.index(b"IDAT")
            data[idat + 4] ^= 0xFF
            path.write_bytes(data)
            with self.assertRaises(ContractError):
                inspect_png(path)

    def test_valid_crc_but_undecodable_idat_is_contract_error(self):
        def chunk(kind, payload):
            crc = binascii.crc32(kind)
            crc = binascii.crc32(payload, crc) & 0xFFFFFFFF
            return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)

        ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
        malformed = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", b"not-zlib") + chunk(b"IEND", b"")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad-zlib.png"
            path.write_bytes(malformed)
            with self.assertRaises(ContractError):
                inspect_png(path)


if __name__ == "__main__":
    unittest.main()
