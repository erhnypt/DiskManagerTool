"""Render assets/icon.svg to PNGs with headless Chromium and pack AppIcon.icns.
Usage: node-free; needs `playwright` for Node (see assets/make_icon.sh)."""
import struct, sys, pathlib

TYPES = {"ic07": 128, "ic08": 256, "ic09": 512, "ic10": 1024,
         "ic11": 32, "ic12": 64, "ic13": 256, "ic14": 512}


def pack(png_dir, out):
    chunks = b""
    for t, px in TYPES.items():
        data = (pathlib.Path(png_dir) / f"{px}.png").read_bytes()
        chunks += t.encode() + struct.pack(">I", len(data) + 8) + data
    pathlib.Path(out).write_bytes(b"icns" + struct.pack(">I", len(chunks) + 8) + chunks)


if __name__ == "__main__":
    pack(sys.argv[1], sys.argv[2])
