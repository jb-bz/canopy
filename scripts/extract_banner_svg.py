"""Build the canopy banner SVG by extracting the tree and block as separate
self-contained SVGs (each with its own viewBox + transform), then composing
them alongside a hand-aligned GitHub Mono text element.

This avoids the potrace coordinate-space pitfalls by reusing potrace's
own wrapper — the same <g transform="translate(0,H) scale(0.1,-0.1)">
that potrace emits.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SRC_PNG = REPO / "docs/assets/canopy-banner.png"
OUT_SVG = REPO / "docs/assets/canopy-banner.svg"


def color_distance_sq(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> int:
    return sum((a - b) ** 2 for a, b in zip(c1, c2))


def extract_layer_mask(img: Image.Image, target_rgb: tuple[int, int, int],
                       tolerance: int) -> Image.Image:
    pixels = img.convert("RGB").load()
    w, h = img.size
    mask = Image.new("1", (w, h), 0)
    out = mask.load()
    tol_sq = tolerance ** 2
    for y in range(h):
        for x in range(w):
            if color_distance_sq(pixels[x, y], target_rgb) <= tol_sq:
                out[x, y] = 1
    return mask


def trace_layer_to_path(mask_pbm: Path) -> str:
    """Run potrace on a PBM and return the COMPLETE <path d="..."> data,
    INCLUDING the leading bounding-box rectangle.

    The full path uses `evenodd` fill-rule so the bounding box acts as a
    clip for the actual shapes. Caller must wrap the path in a <g> with
    potrace's standard transform: translate(0,H) scale(0.1,-0.1).
    """
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
        out = Path(tmp.name)
    subprocess.run(
        [
            "potrace", "--svg", "--output", str(out),
            "--turdsize", "2", "--alphamax", "1.0",
            "--opttolerance", "0.2",
            "--tight",
            str(mask_pbm),
        ],
        check=True, capture_output=True,
    )
    text = out.read_text()
    out.unlink()
    m = re.search(r'd="([^"]+)"', text)
    if not m:
        raise RuntimeError(f"potrace output had no d=: {text[:500]}")
    return m.group(1)


def main() -> None:
    print(f"Loading {SRC_PNG}...")
    img = Image.open(SRC_PNG)
    w, h = img.size
    print(f"  size: {w}x{h}")

    tree_rgb = (96, 192, 112)
    block_rgb = (48, 80, 112)

    print("Extracting tree mask...")
    tree_mask = extract_layer_mask(img, tree_rgb, tolerance=30)
    print("Extracting block mask...")
    block_mask = extract_layer_mask(img, block_rgb, tolerance=25)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        tree_pbm = td / "tree.pbm"
        block_pbm = td / "block.pbm"
        tree_mask.save(tree_pbm)
        block_mask.save(block_pbm)

        print("Tracing tree...")
        tree_d = trace_layer_to_path(tree_pbm)
        print(f"  path length: {len(tree_d)} chars")
        print("Tracing block...")
        block_d = trace_layer_to_path(block_pbm)
        print(f"  path length: {len(block_d)} chars")

    # Final SVG. The traced paths use potrace's coordinate convention
    # (pixels × 10, with origin at top-left after scale -0.1 flips Y).
    # Wrap them in <g transform="translate(0,H) scale(0.1,-0.1)"> to map
    # them back to pixel coords with correct orientation.
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {w} {h}"
     width="{w}" height="{h}"
     role="img" aria-label="canopy logo">
  <title>canopy</title>
  <desc>canopy — a stylized green circuit-tree glyph beside the wordmark "CANOPY" set in GitHub Mono, over a dark navy field with a translucent indigo block behind the wordmark.</desc>

  <defs>
    <style type="text/css"><![CDATA[
      @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700;800&display=swap');
      .wordmark {{
        font-family: "JetBrains Mono", "GitHub Mono", "SF Mono", ui-monospace,
                     "Cascadia Code", Menlo, Consolas, "Liberation Mono", monospace;
        font-weight: 700;
        font-size: 170px;
        letter-spacing: 8px;
        fill: #7088a8;
        fill-opacity: 0.85;
      }}
    ]]></style>
  </defs>

  <!-- Dark navy background -->
  <rect x="0" y="0" width="{w}" height="{h}" fill="#101020"/>

  <!-- All traced layers share potrace's pixel coordinate system
       (pixels × 10, Y-flipped). The transform converts back to normal SVG coords.
       fill-rule="evenodd" lets potrace's bounding-box subpath clip the actual
       shapes to the original bitmap bounds. -->
  <g transform="translate(0,{h}) scale(0.1,-0.1)" fill-rule="evenodd">

    <!-- Translucent indigo block behind the wordmark -->
    <path d="{block_d}" fill="#305070" fill-opacity="0.85"/>

    <!-- Stylized green tree -->
    <path d="{tree_d}" fill="#60c070"/>

  </g>

  <!-- Wordmark: vector GitHub Mono. The indigo block's center in the source
       is roughly x=595, y=224 (block extends y=153..295). Baseline ≈ y=290.
       This element lives OUTSIDE the traced-coord transform so font-size
       stays in normal SVG units. -->
  <text class="wordmark" x="595" y="290" text-anchor="middle">CANOPY</text>
</svg>
'''
    OUT_SVG.write_text(svg)
    print(f"\nWrote {OUT_SVG} ({OUT_SVG.stat().st_size} bytes)")


if __name__ == "__main__":
    main()