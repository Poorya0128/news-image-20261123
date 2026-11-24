#!/usr/bin/env python3
"""Entry point for the make.fun bounty news-image-20261123.

Copies the pre-rendered entry.png (next to this file) into the directory
named by MAKEFUN_OUTPUT_DIR. Standard library only.
"""

import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "entry.png")
MAX_BYTES = 1048576  # 1 MiB


def validate_png(data):
    """Check the PNG signature, every chunk CRC, and that the IHDR is
    1024x1024. Raises ValueError on any problem."""
    if len(data) < 8 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("bad PNG signature")
    if len(data) > MAX_BYTES:
        raise ValueError("entry.png is %d bytes, over the 1 MiB limit"
                         % len(data))
    pos = 8
    seen_ihdr = False
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        end = pos + 12 + length
        if end > len(data):
            raise ValueError("truncated chunk %r" % ctype)
        stored_crc = struct.unpack(">I", data[end - 4:end])[0]
        actual_crc = zlib.crc32(ctype + data[pos + 8:end - 4]) & 0xFFFFFFFF
        if stored_crc != actual_crc:
            raise ValueError("CRC mismatch in chunk %r" % ctype)
        if ctype == b"IHDR":
            if length != 13:
                raise ValueError("bad IHDR length")
            w, h = struct.unpack(">II", data[pos + 8:pos + 16])
            if (w, h) != (1024, 1024):
                raise ValueError("IHDR is %dx%d, not 1024x1024" % (w, h))
            seen_ihdr = True
        pos = end
    if not seen_ihdr:
        raise ValueError("no IHDR chunk")
    if pos != len(data):
        raise ValueError("trailing bytes after IEND")


def main():
    with open(SRC, "rb") as f:
        data = f.read()
    validate_png(data)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "entry.png")
    with open(dst, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes)" % (dst, len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
