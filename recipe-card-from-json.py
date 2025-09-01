#!/usr/bin/env python3
"""
Generate a multi-page recipe PDF from a JSON file.

USAGE:
    python generate_recipe_from_json.py --json recipe.json --out recipe.pdf

JSON shape (abridged):
{
  "title": "Milkbar Carrot Graham Cake",
  "version": "v0.0.0",
  "line_length": 420,
  "components": [
    {
      "name": "Carrot Cake",
      "equipment": [["Quarter-sheet pan 9×13 in (23×33 cm)"]],  # optional, single-column rows
      "ingredients": [["Butter, room temp", "230 grams"], ...],   # list of [name, amount]
      "instructions": ["Heat the oven to 350°F.", ...]            # list of strings
    },
    ...
  ]
}
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ReportLab
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# -----------------------------------------------------------------------------
# Load & validate
# -----------------------------------------------------------------------------

def load_recipe_json(path: Path) -> Dict[str, Any]:
    """Load and minimally validate the recipe JSON."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: JSON file not found: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: Failed to parse JSON: {e}")

    if not isinstance(data, dict):
        raise SystemExit("ERROR: Top-level JSON must be an object.")
    if "components" not in data or not isinstance(data["components"], list):
        raise SystemExit("ERROR: JSON must contain a 'components' array.")

    # Soft warnings (not fatal)
    if "title" not in data:
        print("WARN: Missing 'title'; defaulting to 'Recipe'.")
    if "version" not in data:
        print("WARN: Missing 'version'; footer will be blank.")
    if "line_length" not in data:
        print("WARN: Missing 'line_length'; defaulting to 420.")

    # Component-level checks
    for idx, comp in enumerate(data["components"], start=1):
        if not isinstance(comp, dict):
            raise SystemExit(f"ERROR: components[{idx}] must be an object.")
        if "name" not in comp:
            raise SystemExit(f"ERROR: components[{idx}] is missing 'name'.")

        if "ingredients" in comp:
            ing = comp["ingredients"]
            if not isinstance(ing, list) or any(
                not isinstance(row, list) or len(row) != 2 for row in ing
            ):
                raise SystemExit(
                    f"ERROR: components[{idx}].ingredients must be a list of [name, amount] pairs."
                )
        if "equipment" in comp:
            eq = comp["equipment"]
            if not isinstance(eq, list) or any(
                not isinstance(row, list) or len(row) != 1 for row in eq
            ):
                raise SystemExit(
                    f"ERROR: components[{idx}].equipment must be a list of single-item rows, e.g. [[\"Quarter-sheet pan\"], ...]."
                )
        if "instructions" in comp:
            ins = comp["instructions"]
            if not isinstance(ins, list) or any(not isinstance(s, str) for s in ins):
                raise SystemExit(
                    f"ERROR: components[{idx}].instructions must be a list of strings."
                )

    return data


# -----------------------------------------------------------------------------
# Page furniture: two rounded rules around the centered component name
# -----------------------------------------------------------------------------

class ComponentBanner(Flowable):
    """
    Component header with two rounded rules (top & bottom), centered horizontally,
    with vertical spacing derived from actual font metrics.

    Behavior (matching the original):
      - Lines are centered and have fixed length = `line_length`
      - Rounded caps: setLineCap(1)
      - Text is centered horizontally
      - Vertical positions use font ascent/descent for optical centering
    """

    def __init__(
        self,
        text: str,
        container_width: float,
        line_length: float,
        line_thickness: float = 2.83465,  # ~1 mm
        color: colors.Color = colors.HexColor("#112c4c"),
        font_name: str = "Helvetica-Bold",
        font_size: float = 16.0,
        gap_above: float = 16.0,
        padding_top: float = 6.0,
        padding_bottom: float = 6.0,
        gap_below: float = 8.0,
        top_text_correction: float = 2.0,  # tiny optical nudge like original
    ) -> None:
        super().__init__()
        self.text = text
        self.container_width = float(container_width)
        self.line_length = float(line_length)
        self.line_thickness = float(line_thickness)
        self.color = color
        self.font_name = font_name
        self.font_size = float(font_size)
        self.gap_above = float(gap_above)
        self.padding_top = float(padding_top) + float(top_text_correction)
        self.padding_bottom = float(padding_bottom)
        self.gap_below = float(gap_below)

        # Font metrics for vertical placement
        face = pdfmetrics.getFont(self.font_name).face
        ascent = face.ascent * self.font_size / 1000.0
        descent = abs(face.descent) * self.font_size / 1000.0
        self.text_height = ascent + descent
        self.text_descent = descent

        # Band between rules (text + paddings)
        self.band_height = self.padding_top + self.text_height + self.padding_bottom

        # Flowable box size
        self.width = self.container_width
        self.height = self.gap_above + self.band_height + self.line_thickness + self.gap_below

    def wrap(self, availWidth: float, availHeight: float) -> Tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        c: Canvas = self.canv
        c.saveState()
        try:
            c.setStrokeColor(self.color)
            c.setFillColor(self.color)
            c.setLineWidth(self.line_thickness)
            c.setLineCap(1)  # rounded

            # Center the rules horizontally at fixed length
            eff_len = min(self.line_length, self.container_width)
            x0 = (self.container_width - eff_len) / 2.0
            x1 = x0 + eff_len

            # Vertical positions for rules and baseline
            y_bottom = self.gap_above
            y_top = self.gap_above + self.band_height
            c.line(x0, y_bottom, x1, y_bottom)
            c.line(x0, y_top, x1, y_top)

            # Centered text baseline inside the band
            text_w = pdfmetrics.stringWidth(self.text, self.font_name, self.font_size)
            tx = (self.container_width - text_w) / 2.0
            baseline_y = self.gap_above + self.padding_bottom + self.text_descent

            c.setFont(self.font_name, self.font_size)
            c.drawString(tx, baseline_y, self.text)
        finally:
            c.restoreState()


def make_footer(version_text: str):
    """Bottom-right version text on each page."""
    version_text = version_text or ""

    def _footer(canvas: Canvas, doc: SimpleDocTemplate) -> None:
        canvas.saveState()
        try:
            margin = 36  # 0.5 in
            font = "Helvetica"
            size = 8
            canvas.setFont(font, size)
            canvas.setFillColor(colors.grey)
            w = canvas.stringWidth(version_text, font, size)
            x = doc.pagesize[0] - margin - w
            y = margin / 2.0
            canvas.drawString(x, y, version_text)
        finally:
            canvas.restoreState()

    return _footer


# -----------------------------------------------------------------------------
# Render
# -----------------------------------------------------------------------------

def build_pdf(json_path: str, out_path: str) -> None:
    data = load_recipe_json(Path(json_path))

    title: str = data.get("title", "Recipe")
    version: str = data.get("version", "")
    line_length: float = float(data.get("line_length", 420))
    components: List[Dict[str, Any]] = data["components"]

    doc = SimpleDocTemplate(
        out_path,
        pagesize=letter,
        rightMargin=72,   # 1.0 in
        leftMargin=72,    # 1.0 in
        topMargin=36,     # 0.5 in
        bottomMargin=36,  # 0.5 in
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="MainTitle",
            fontName="Helvetica-Bold",
            fontSize=24,
            textColor=colors.HexColor("#112c4c"),
            alignment=1,  # center
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="InstructionHeader",
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=colors.HexColor("#4682B4"),  # steelblue
            spaceBefore=12,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="InstructionBlock",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            spaceBefore=2,
            spaceAfter=6,
        )
    )

    def style_headered_table(table: Table) -> None:
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4682B4")),  # steelblue
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ]
            )
        )

    story: List[Any] = []

    for idx, comp in enumerate(components):
        if idx > 0:
            story.append(PageBreak())

        # Same title on each component page (as in original output)
        story.append(Paragraph(title, styles["MainTitle"]))

        # Component header with TWO rounded rules, centered
        story.append(
            ComponentBanner(
                text=comp["name"],
                container_width=doc.width,
                line_length=line_length,
                line_thickness=2.83465,
                color=colors.HexColor("#112c4c"),
                font_name="Helvetica-Bold",
                font_size=16,
                gap_above=16,
                padding_top=6,
                padding_bottom=6,
                gap_below=8,
                top_text_correction=2,
            )
        )
        story.append(Spacer(1, 12))

        # Optional equipment (single-column)
        equipment: List[List[str]] = comp.get("equipment", [])
        if equipment:
            eq_table = Table([["Equipment"]] + equipment, colWidths=[doc.width], hAlign="LEFT")
            style_headered_table(eq_table)
            story.append(eq_table)
            story.append(Spacer(1, 12))

        # Ingredients table
        ingredients: List[List[str]] = comp.get("ingredients", [])
        if ingredients:
            ing_table = Table(
                [["Ingredient", "Amount"]] + ingredients,
                colWidths=[doc.width * 0.65, doc.width * 0.35],
                hAlign="LEFT",
            )
            style_headered_table(ing_table)
            story.append(ing_table)

        # Instructions
        instructions: List[str] = comp.get("instructions", [])
        if instructions:
            story.append(Paragraph("Instructions", styles["InstructionHeader"]))
            for step in instructions:
                story.append(Paragraph(step, styles["InstructionBlock"]))

    footer = make_footer(version)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def parse_args(argv: Optional[Sequence[str]] = None):
    ap = argparse.ArgumentParser(description="Render a recipe PDF from JSON.")
    ap.add_argument("--json", required=True, help="Path to recipe JSON file")
    ap.add_argument("--output", required=True, help="Output PDF path")
    return ap.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    build_pdf(args.json, args.output)


if __name__ == "__main__":
    main()
