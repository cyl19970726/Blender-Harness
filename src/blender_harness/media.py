from __future__ import annotations

import binascii
import struct
import zlib
from pathlib import Path
from typing import Any, Dict

from .io import ContractError, sha256_file


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _png_chunks(data: bytes, path: Path):
    offset = len(PNG_MAGIC)
    while offset < len(data):
        if offset + 12 > len(data):
            raise ContractError("PNG has a truncated chunk header: %s" % path)
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            raise ContractError("PNG has a truncated %r chunk: %s" % (chunk_type, path))
        payload = data[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length : chunk_end])[0]
        actual_crc = binascii.crc32(chunk_type)
        actual_crc = binascii.crc32(payload, actual_crc) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise ContractError("PNG chunk CRC mismatch for %r: %s" % (chunk_type, path))
        yield chunk_type, payload
        offset = chunk_end
        if chunk_type == b"IEND":
            if offset != len(data):
                raise ContractError("PNG contains bytes after IEND: %s" % path)
            return
    raise ContractError("PNG is missing IEND: %s" % path)


def inspect_png(path: Path) -> Dict[str, Any]:
    try:
        data = path.read_bytes()
    except FileNotFoundError as exc:
        raise ContractError("missing PNG: %s" % path) from exc
    if len(data) < 33 or not data.startswith(PNG_MAGIC):
        raise ContractError("file does not have a valid PNG signature: %s" % path)
    chunks = list(_png_chunks(data, path))
    if not chunks or chunks[0][0] != b"IHDR" or len(chunks[0][1]) != 13:
        raise ContractError("PNG does not start with a valid IHDR: %s" % path)
    if chunks[-1][0] != b"IEND" or chunks[-1][1]:
        raise ContractError("PNG does not end with a valid IEND: %s" % path)
    ihdr = chunks[0][1]
    width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", ihdr)
    if width <= 0 or height <= 0:
        raise ContractError("PNG dimensions must be positive: %s" % path)
    if compression != 0 or filtering != 0 or interlace not in {0, 1}:
        raise ContractError("PNG uses unsupported header methods: %s" % path)
    channels_by_color_type = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    channels = channels_by_color_type.get(color_type)
    allowed_depths = {
        0: {1, 2, 4, 8, 16},
        2: {8, 16},
        3: {1, 2, 4, 8},
        4: {8, 16},
        6: {8, 16},
    }
    if channels is None or bit_depth not in allowed_depths[color_type]:
        raise ContractError("PNG has an invalid color type/bit depth: %s" % path)
    compressed = b"".join(payload for chunk_type, payload in chunks if chunk_type == b"IDAT")
    if not compressed:
        raise ContractError("PNG has no IDAT image data: %s" % path)
    try:
        decoder = zlib.decompressobj()
        pixels = decoder.decompress(compressed) + decoder.flush()
    except zlib.error as exc:
        raise ContractError("PNG IDAT stream cannot be decoded: %s" % path) from exc
    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ContractError("PNG IDAT stream has trailing or incomplete compressed data: %s" % path)
    # Exact scanline validation is straightforward for the non-interlaced PNGs
    # emitted by Blender. For Adam7 files, successful zlib decoding plus chunk
    # and CRC validation remains the fail-closed structural check.
    if interlace == 0:
        row_bytes = (width * channels * bit_depth + 7) // 8
        expected = height * (row_bytes + 1)
        if len(pixels) != expected:
            raise ContractError("PNG decoded byte count does not match IHDR: %s" % path)
        for row in range(height):
            if pixels[row * (row_bytes + 1)] > 4:
                raise ContractError("PNG has an invalid scanline filter: %s" % path)
    return {
        "media_type": "image/png",
        "width": width,
        "height": height,
        "size_bytes": len(data),
        "sha256": sha256_file(path),
    }
