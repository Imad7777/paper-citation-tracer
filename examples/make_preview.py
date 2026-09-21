"""Compose a before/after side-by-side preview PNG for the README.

Run from the repo root after make_demo.py + highlight_citations.py:
    python examples/make_preview.py
"""

from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
LBL = 56
GAP = 48


def page_image(pdf: Path) -> Image.Image:
    doc = fitz.open(pdf)
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(1.3, 1.3), alpha=False)
    doc.close()
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    # thin border
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width - 1, img.height - 1], outline=(210, 210, 214))
    return img


def main() -> None:
    left = page_image(HERE / "sample_paper.pdf")
    right = page_image(HERE / "sample_paper_highlighted.pdf")
    W = left.width + GAP + right.width
    H = LBL + max(left.height, right.height) + 24

    canvas = Image.new("RGB", (W, H), (250, 250, 251))
    canvas.paste(left, (0, LBL))
    canvas.paste(right, (left.width + GAP, LBL))

    d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    d.text((left.width // 2 - 50, 14), "before", fill=(90, 94, 104), font=font)
    d.text((left.width + GAP + right.width // 2 - 40, 14), "after",
           fill=(90, 94, 104), font=font)

    out = HERE / "preview.png"
    canvas.save(out)
    print(f"saved {out} ({canvas.width}x{canvas.height})")


if __name__ == "__main__":
    main()
