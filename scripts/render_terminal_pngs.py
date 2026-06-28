"""Render command outputs as styled terminal PNGs for the README.

Takes plain text (the stdout of various `canopy` commands) and renders
each as a PNG with:
  - dark navy background (matches the canopy brand)
  - monospace font (DejaVu Sans Mono, ships with matplotlib)
  - syntax-light colorization (keywords, paths, flags)
  - padded to look like a terminal screenshot

Output: docs/screenshots/{cmd-name}.png
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "docs/screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Colors (Catppuccin Mocha palette — matches what most agent UIs use)
BG = (30, 30, 46)
FG = (205, 214, 244)
DIM = (127, 132, 156)
ACCENT = (137, 180, 250)   # blue for headings
GREEN = (166, 227, 161)    # success / paths
YELLOW = (250, 245, 169)   # flags
RED = (243, 139, 168)      # errors (not used in these captures)

# Try to find a good monospace font.
FONT_PATHS = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/SFNSMono.ttf",
    "/System/Library/Fonts/Monaco.ttf",
    "/Library/Fonts/Courier New.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/opt/homebrew/share/fonts/.../JetBrainsMono-Regular.ttf",
]
FONT = None
for fp in FONT_PATHS:
    if Path(fp).exists():
        try:
            FONT = ImageFont.truetype(fp, 14)
            FONT_BOLD = ImageFont.truetype(fp, 14)
            FONT_TITLE = ImageFont.truetype(fp, 16)
            break
        except OSError:
            continue
if FONT is None:
    # Fall back to PIL's default bitmap font (ugly but works)
    FONT = ImageFont.load_default()
    FONT_BOLD = FONT
    FONT_TITLE = FONT

PADDING = 24
LINE_HEIGHT = 20
TITLE_HEIGHT = 36


def measure(text: str, font) -> tuple[int, int]:
    """Return (width, height) for rendered text."""
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def render(text: str, out_path: Path, *, title: str | None = None,
           width: int = 900) -> None:
    lines = text.splitlines()
    title_h = TITLE_HEIGHT if title else 0

    # Compute width based on longest line.
    max_w = width - 2 * PADDING
    for line in lines:
        w, _ = measure(line, FONT)
        max_w = max(max_w, w)
    img_w = max_w + 2 * PADDING

    # Compute height.
    img_h = title_h + len(lines) * LINE_HEIGHT + 2 * PADDING

    img = Image.new("RGB", (img_w, img_h), BG)
    draw = ImageDraw.Draw(img)

    # Title bar (if provided)
    y = PADDING
    if title:
        # macOS-style 3 traffic lights (decorative)
        for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            cx = PADDING + i * 22
            draw.ellipse((cx, PADDING + 6, cx + 14, PADDING + 20), fill=c)
        # Title text
        tw, th = measure(title, FONT_TITLE)
        draw.text((PADDING + 80, PADDING + 6), title, fill=ACCENT, font=FONT_TITLE)
        # Separator line
        y = PADDING + TITLE_HEIGHT
        draw.line((PADDING, y, img_w - PADDING, y), fill=DIM, width=1)
        y += 8

    # Render each line.
    for line in lines:
        x = PADDING
        # Color the prompt portion of the line.
        # Format: "(.venv) user@host path $ command"
        m = re.match(r"^(\(.+?\)\s*)(\S+@\S+\s+)(.+?)(\$\s)(.*)$", line)
        if m:
            venv, user, path, prompt, rest = m.groups()
            draw.text((x, y), venv, fill=GREEN, font=FONT_BOLD)
            x += measure(venv, FONT_BOLD)[0]
            draw.text((x, y), user, fill=DIM, font=FONT)
            x += measure(user, FONT)[0]
            draw.text((x, y), path, fill=ACCENT, font=FONT_BOLD)
            x += measure(path, FONT_BOLD)[0]
            draw.text((x, y), prompt, fill=DIM, font=FONT)
            x += measure(prompt, FONT)[0]
            _colorize(draw, rest, x, y)
        else:
            _colorize(draw, line, x, y)
        y += LINE_HEIGHT

    img.save(out_path, "PNG", optimize=True)
    print(f"  wrote {out_path} ({img_w}x{img_h}, {out_path.stat().st_size // 1024} KB)")


def _colorize(draw: ImageDraw.ImageDraw, text: str, x: int, y: int) -> None:
    """Draw `text` at (x, y), applying simple color rules."""
    # Highlight section banners like =====SHOW=====.
    if re.match(r"^=+[A-Z]+=+$", text):
        draw.text((x, y), text, fill=ACCENT, font=FONT_BOLD)
        return
    # Highlight canopy subcommand labels.
    if text.lstrip().startswith(("usage:", "canopy v", "positional arguments:",
                                  "options:", "  -", "  --")):
        draw.text((x, y), text, fill=FG, font=FONT)
        return
    # Highlight descriptions (the comment part after a path).
    if "  # " in text:
        path_part, _, desc_part = text.partition("  # ")
        draw.text((x, y), path_part, fill=GREEN, font=FONT)
        off = measure(path_part, FONT)[0]
        draw.text((x + off, y), "  # ", fill=DIM, font=FONT)
        off += measure("  # ", FONT)[0]
        draw.text((x + off, y), desc_part, fill=YELLOW, font=FONT)
        return
    # Highlight `path :: description` (explore format).
    if " :: " in text:
        path_part, _, desc_part = text.partition(" :: ")
        draw.text((x, y), path_part, fill=GREEN, font=FONT)
        off = measure(path_part, FONT)[0]
        draw.text((x + off, y), " :: ", fill=DIM, font=FONT)
        off += measure(" :: ", FONT)[0]
        draw.text((x + off, y), desc_part, fill=YELLOW, font=FONT)
        return
    # Default.
    draw.text((x, y), text, fill=FG, font=FONT)


def main() -> None:
    captures = [
        ("01-help",     "canopy --help",                                    "canopy --help"),
        ("02-version",  "canopy --version",                                 "canopy --version"),
        ("03-show",     "canopy show --depth 2",                             "canopy show --depth 2"),
        ("04-explore",  "canopy explore (post-fill)",                        "canopy explore"),
        ("05-check",    "canopy check (CI mode)",                            "canopy check"),
        ("06-fill",     "canopy fill --batch 5 --max-words 12",             "canopy fill"),
    ]
    for slug, command, title in captures:
        txt_path = Path(f"/tmp/out-{slug.split('-', 1)[1]}.txt")
        if slug == "01-help":
            txt_path = Path("/tmp/out-help.txt")
        elif slug == "02-version":
            txt_path = Path("/tmp/out-version.txt")
        elif slug == "03-show":
            txt_path = Path("/tmp/out-show.txt")
        elif slug == "04-explore":
            txt_path = Path("/tmp/out-explore.txt")
        elif slug == "05-check":
            txt_path = Path("/tmp/out-check.txt")
        elif slug == "06-fill":
            txt_path = Path("/tmp/canopy-fill-output.txt")
        if not txt_path.exists():
            print(f"  skip {slug} (no {txt_path})")
            continue
        text = txt_path.read_text()
        # Wrap in a fake shell prompt so the rendering includes a prompt line.
        prompt = "(.venv) canopy@canopy ~/canopy $ "
        body = "\n".join(f"{prompt}{line}" if i == 0 else f"            {line}"
                          for i, line in enumerate([command] + text.splitlines()[1:]))
        out_path = OUT_DIR / f"{slug}.png"
        render(body, out_path, title=title)
    print("done.")


if __name__ == "__main__":
    main()