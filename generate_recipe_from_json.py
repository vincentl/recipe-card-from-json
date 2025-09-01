#!/usr/bin/env python3
"""
Generate a multi-page recipe PDF from a JSON file.

USAGE:
    python generate_recipe_from_json.py --json recipe.json --out recipe.pdf

JSON SCHEMA (see template for a filled example):
{
  "title": "Milkbar Carrot Graham Cake",
  "version": "v0.0.0",
  "line_length": 420,
  "components": [
    {
      "name": "Carrot Cake",
      "ingredients": [["Butter, room temp", "230 g"], ["Light brown sugar", "240 g"], ...],
      "instructions": ["Step text ...", "Next step ...", ...]
    },
    ...
  ]
}
"""
import json, argparse
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak, Spacer, Flowable
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics

# ---- Banner Flowable ----
class ComponentBanner(Flowable):
    def __init__(self, text, container_width, line_length, line_thickness, color,
                 fontName="Helvetica-Bold", fontSize=16,
                 padding_bottom=6, padding_top=6, top_correction=2,
                 gap_above=16, gap_below=8):
        Flowable.__init__(self)
        self.text = text
        self.container_width = container_width
        self.line_length = line_length
        self.line_thickness = line_thickness
        self.color = color
        self.fontName = fontName
        self.fontSize = fontSize
        self.padding_bottom = padding_bottom
        self.padding_top = padding_top + top_correction   # optical +2pt
        self.gap_above = gap_above
        self.gap_below = gap_below
        face = pdfmetrics.getFont(self.fontName).face
        ascent = face.ascent * self.fontSize / 1000.0
        descent = abs(face.descent) * self.fontSize / 1000.0
        self.text_height = ascent + descent
        self.text_descent = descent
        self.band_height = self.padding_bottom + self.text_height + self.padding_top
        self.width = self.container_width
        self.height = self.gap_above + self.band_height + self.line_thickness + self.gap_below

    def draw(self):
        c = self.canv
        c.setStrokeColor(self.color)
        c.setFillColor(self.color)
        c.setLineWidth(self.line_thickness)
        c.setLineCap(1)  # rounded caps
        x0 = (self.container_width - self.line_length) / 2.0
        x1 = x0 + self.line_length
        y_bottom = self.gap_above
        y_top = self.gap_above + self.band_height
        c.line(x0, y_bottom, x1, y_bottom)
        c.line(x0, y_top, x1, y_top)
        text_width = pdfmetrics.stringWidth(self.text, self.fontName, self.fontSize)
        tx = (self.container_width - text_width) / 2.0
        baseline_y = self.gap_above + self.padding_bottom + self.text_descent
        c.setFont(self.fontName, self.fontSize)
        c.drawString(tx, baseline_y, self.text)

def build_pdf(json_path, out_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    version = data.get("version")

    def _footer(canvas, doc):
        if not version:
            return
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        try:
            canvas.setFillGray(0.6)
        except Exception:
            pass
        text = version
        tw = canvas.stringWidth(text, "Helvetica", 8)
        x = doc.pagesize[0] - doc.rightMargin - tw
        y = doc.bottomMargin
        canvas.drawString(x, y, text)
        canvas.restoreState()


    title = data.get("title", "Milkbar Recipe")
    components = data["components"]
    line_length = data.get("line_length", 420)

    doc = SimpleDocTemplate(out_path, pagesize=letter,
                            rightMargin=72, leftMargin=72, topMargin=36, bottomMargin=36)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='MainTitle',
                              fontName="Helvetica-Bold", fontSize=24,
                              textColor=colors.HexColor("#112c4c"),
                              alignment=1, spaceAfter=12))
    styles.add(ParagraphStyle(name='InstructionHeader',
                              fontName="Helvetica-Bold", fontSize=12,
                              textColor=colors.steelblue,
                              spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name='InstructionBlock',
                              parent=styles['Normal'],
                              fontName="Helvetica", fontSize=11,
                              spaceBefore=2, spaceAfter=6, leading=14))

    story = []
    for i, comp in enumerate(components):
        if i > 0:
            story.append(PageBreak())

        story.append(Paragraph(title, styles['MainTitle']))
        story.append(ComponentBanner(
            text=comp["name"],
            container_width=doc.width,
            line_length=line_length,
            line_thickness=2.83465,
            color=colors.HexColor("#112c4c"),
            fontName="Helvetica-Bold",
            fontSize=16,
            padding_bottom=6,
            padding_top=6,
            top_correction=2,
            gap_above=16,   # 1em above
            gap_below=8     # 0.5em below
        ))
        story.append(Spacer(1, 12))
        
        # equipment table exactly the text width
        equipment = comp.get("equipment", [])
        if equipment:
            table = Table([["Equipment"]] + equipment,
                          colWidths=[doc.width], hAlign='LEFT', spaceAfter=12)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.steelblue),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), "Helvetica-Bold"),
                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ]))
            story.append(table)

        # Ingredients table exactly the text width
        ingredients = comp.get("ingredients", [])
        if ingredients:
            table = Table([["Ingredient", "Amount"]] + ingredients,
                          colWidths=[doc.width*0.65, doc.width*0.35], hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.steelblue),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), "Helvetica-Bold"),
                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ]))
            story.append(table)

        # Instructions
        instructions = comp.get("instructions", [])
        if instructions:
            story.append(Paragraph("Instructions", styles['InstructionHeader']))
            for step in instructions:
                story.append(Paragraph(step, styles['InstructionBlock']))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)

if __name__ == "__main__":
    import sys, argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True, help="Path to recipe JSON file")
    ap.add_argument("--out", required=True, help="Output PDF path")
    args = ap.parse_args()
    build_pdf(args.json, args.out)