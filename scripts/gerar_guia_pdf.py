from pathlib import Path
import re
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "Guia_Apresentacao.md"
OUTPUT = ROOT / "docs" / "Guia_Apresentacao.pdf"
PAGE_SIZE = (8.27, 11.69)


def plain_text(value):
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"\*(.*?)\*", r"\1", value)
    return value.strip()


def main():
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    pages = PdfPages(OUTPUT)
    page_number = 0
    figure = None
    axis = None
    y = 0.91

    def new_page():
        nonlocal page_number, figure, axis, y
        if figure is not None:
            axis.text(0.5, 0.035, f"FBS Distribuição · Guia de apresentação · {page_number}",
                      ha="center", va="center", fontsize=8, color="#64748b")
            pages.savefig(figure, bbox_inches="tight")
            plt.close(figure)
        page_number += 1
        figure, axis = plt.subplots(figsize=PAGE_SIZE)
        figure.patch.set_facecolor("white")
        axis.set_xlim(0, 1)
        axis.set_ylim(0, 1)
        axis.axis("off")
        axis.text(0.08, 0.965, "ASSISTENTE OPERACIONAL · FBS DISTRIBUIÇÃO",
                  fontsize=8, color="#0f766e", weight="bold", va="top")
        axis.plot([0.08, 0.92], [0.945, 0.945], color="#cbd5e1", linewidth=0.8)
        y = 0.91

    def draw(text, fontsize=9.2, color="#1f2937", weight="normal",
             indent=0.0, gap=0.008, line_step=None):
        nonlocal y
        text = plain_text(text)
        width = max(42, int(99 * 9.2 / fontsize))
        wrapped = textwrap.wrap(text, width=width, break_long_words=True,
                                break_on_hyphens=False) or [""]
        step = line_step or fontsize / 470
        required = step * len(wrapped) + gap
        if y - required < 0.075:
            new_page()
        for line in wrapped:
            axis.text(0.08 + indent, y, line, ha="left", va="top",
                      fontsize=fontsize, color=color, weight=weight)
            y -= step
        y -= gap

    new_page()
    in_code = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            y -= 0.003
            continue
        if not stripped:
            y -= 0.006
            continue
        if stripped.startswith("|") and set(stripped.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        if stripped.startswith("# "):
            draw(stripped[2:], fontsize=22, color="#0f172a", weight="bold",
                 gap=0.02, line_step=0.042)
        elif stripped.startswith("## "):
            draw(stripped[3:], fontsize=14, color="#0f766e", weight="bold",
                 gap=0.012, line_step=0.029)
        elif stripped.startswith("### "):
            draw(stripped[4:], fontsize=10.5, color="#334155", weight="bold",
                 gap=0.008, line_step=0.023)
        elif stripped.startswith("- "):
            draw("• " + stripped[2:], fontsize=9.0, indent=0.015, gap=0.004)
        elif re.match(r"^\d+\.\s", stripped):
            draw(stripped, fontsize=9.0, indent=0.01, gap=0.004)
        elif stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            draw("   •   ".join(cells), fontsize=8.3, indent=0.01, gap=0.004)
        elif in_code:
            draw(stripped, fontsize=8.5, color="#334155", indent=0.02,
                 gap=0.003, line_step=0.018)
        else:
            draw(stripped, fontsize=9.2, gap=0.008)

    axis.text(0.5, 0.035, f"FBS Distribuição · Guia de apresentação · {page_number}",
              ha="center", va="center", fontsize=8, color="#64748b")
    pages.savefig(figure, bbox_inches="tight")
    plt.close(figure)
    pages.close()
    print(f"PDF criado: {OUTPUT}")


if __name__ == "__main__":
    main()
