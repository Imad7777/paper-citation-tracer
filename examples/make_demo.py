"""Create a small fake 'paper' PDF that contains the classic matching traps
(smart quotes, ligature, line-broken phrase, de-hyphenation), then run the
highlighter CLI on it for the README demo.

Output: examples/sample_paper.pdf

Run from the repo root:
    python examples/make_demo.py
"""

from pathlib import Path

import fitz

HERE = Path(__file__).parent
OUT = HERE / "sample_paper.pdf"

TITLE = "Customer Experience: A Holistic Perspective"

PARAS = [
    # abstract-style paragraph containing the definition sentence
    "Abstract. In this conceptual note we argue that customer experience is "
    "holistic in nature and involves cognitive, affective, emotional, social "
    "and physical responses to the retailer. Prior work has treated the "
    "construct as a unidimensional satisfaction measure, which we consider "
    "too narrow for omnichannel contexts.",

    # paragraph with smart quote + ligature traps
    "Verhoef et al. (2009, p. 32) explicitly define the construct as "
    "\u201ca customer\u2019s internal and subjective response\u201d, and stress "
    "that the \ufb01rm\u2019s touchpoints shape it jointly. This de\ufb01nition "
    "remains in\ufb02uential in services marketing research.",

    # paragraph with a de-hyphenated word and a second occurrence of the
    # definition phrase
    "Servicescape research similarly suggests that the physical environment "
    "is cogni- tively appraised before any affective response occurs, which "
    "explains why holistic in nature and involves remains a robust summary "
    "of the construct across contexts.",
]


def _times(page: fitz.Page) -> str:
    """Embed real Times New Roman so ligatures and smart quotes survive."""
    fontfile = r"C:\Windows\Fonts\times.ttf"
    name = "TNR"
    if Path(fontfile).exists():
        page.insert_font(fontname=name, fontfile=fontfile)
        return name
    return "times-roman"


def build() -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    font = _times(page)

    y = 72
    page.insert_text((72, y), TITLE, fontsize=15, fontname=font)
    y += 10
    page.draw_line(fitz.Point(72, y), fitz.Point(523, y), width=0.7)
    y += 24

    for para in PARAS:
        rect = fitz.Rect(72, y, 523, y + 120)
        page.insert_textbox(rect, para, fontsize=10.5, fontname=font,
                            align=fitz.TEXT_ALIGN_LEFT)
        y = rect.y1 + 22

    page.insert_text((72, 800), "1", fontsize=10, fontname=font)
    doc.save(OUT, deflate=True)
    doc.close()
    print(f"built {OUT}")


if __name__ == "__main__":
    build()
