#!/usr/bin/env python3
"""Split the 3x2 icon sheet into 6 transparent-background PNGs.

Usage:
    python3 docs/crop_icons.py <source-image> [output-dir]

Method: the sheet background is white, but icons also contain white fills
(checkmark, document bodies), so plain "white -> transparent" would punch
holes in the icons. Instead we flood-fill ONLY the white region connected
to the image borders and make just that transparent; enclosed whites stay
opaque. Edge pixels get feathered alpha to avoid halos.
"""

import os
import sys
from collections import deque

from PIL import Image

NAMES = [
    "icon-free.png",      # top-left:    seal + checkmark (available)
    "icon-batch.png",     # top-middle:  stacked docs (batch checks)
    "icon-csv.png",       # top-right:   document + CSV (CSV export)
    "icon-web.png",       # bottom-left: browser + RTL/LTR (Persian web UI)
    "icon-cli.png",       # bottom-mid:  terminal (CLI)
    "icon-reserved.png",  # bottom-right: shield + lock (reserved)
]

WHITE_TOL = 42      # color distance from white to count as background
FEATHER = 48.0      # feather range for edge alpha
TRIM_TOL = 24       # non-background threshold for auto-trim bbox


def dist_white(px):
    r, g, b = px[:3]
    return ((255 - r) ** 2 + (255 - g) ** 2 + (255 - b) ** 2) ** 0.5


def background_mask(img):
    """Boolean mask of background: near-white pixels connected to the border."""
    w, h = img.size
    px = img.load()
    mask = bytearray(w * h)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            q.append((x, y))
    while q:
        x, y = q.popleft()
        i = y * w + x
        if mask[i]:
            continue
        if dist_white(px[x, y]) > WHITE_TOL:
            continue
        mask[i] = 1
        if x > 0:
            q.append((x - 1, y))
        if x < w - 1:
            q.append((x + 1, y))
        if y > 0:
            q.append((x, y - 1))
        if y < h - 1:
            q.append((x, y + 1))
    return mask


def apply_transparency(cell):
    """Make border-connected background transparent with feathered edges."""
    cell = cell.convert("RGB")
    w, h = cell.size
    mask = background_mask(cell)
    out = Image.new("RGBA", (w, h))
    src, dst = cell.load(), out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = src[x, y]
            if mask[y * w + x]:
                d = dist_white((r, g, b))
                alpha = int(255 * min(1.0, d / FEATHER))
                dst[x, y] = (r, g, b, alpha)
            else:
                dst[x, y] = (r, g, b, 255)
    return out


def autocrop(img):
    """Trim near-white margins around the icon, keeping small padding."""
    w, h = img.size
    rgb = img.convert("RGB")
    px = rgb.load()
    minx, miny, maxx, maxy = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            if dist_white(px[x, y]) > TRIM_TOL:
                if x < minx:
                    minx = x
                if x > maxx:
                    maxx = x
                if y < miny:
                    miny = y
                if y > maxy:
                    maxy = y
    if maxx < 0:
        return img
    pad = int(max(w, h) * 0.04)
    minx = max(0, minx - pad)
    miny = max(0, miny - pad)
    maxx = min(w - 1, maxx + pad)
    maxy = min(h - 1, maxy + pad)
    return img.crop((minx, miny, maxx + 1, maxy + 1))


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 docs/crop_icons.py <source-image> [output-dir]")
        sys.exit(1)
    src = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join("docs", "icons")
    os.makedirs(outdir, exist_ok=True)

    sheet = Image.open(src).convert("RGB")
    w, h = sheet.size
    print(f"sheet: {w}x{h}")
    cw, ch = w // 3, h // 2
    for idx, name in enumerate(NAMES):
        col, row = idx % 3, idx // 3
        cell = sheet.crop((col * cw, row * ch, (col + 1) * cw, (row + 1) * ch))
        cell = autocrop(cell)
        cell = apply_transparency(cell)
        path = os.path.join(outdir, name)
        cell.save(path)
        print(f"saved {path} ({cell.size[0]}x{cell.size[1]})")


if __name__ == "__main__":
    main()
