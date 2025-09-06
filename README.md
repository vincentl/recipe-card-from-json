# Generating PDF Recipe Pages from JSON

This project uses **structured JSON files** together with a **ReportLab-based Python script** to generate formatted recipe PDFs.

As examples, several **Milk Bar cake recipes** that were publicly available on [milkbarstore.com](https://milkbarstore.com/blogs/recipes) as of **August 31, 2025** were adapted. These versions are scaled for an **8-inch cake ring** instead of the original 6-inch ring.

_All rights to the original recipes and branding belong to **Milk Bar**. This repo is not affiliated with Milk Bar; it is simply a technical demonstration using their publicly available recipes as a case study._

## Contents

- `recipe-card-from-json.py` — PDF generator using ReportLab
- `milkbar_carrot_graham_cake.json`
  - Scaled from 6-inch cake to 8-inch cake
  - Graham frosting: reduced kosher salt by omitting the final 1-gram addition
- `milkbar_birthday_cake.json`
  - Scaled from 6-inch cake to 8-inch cake
- `milkbar_chocolate_cake.json`
  - Scaled from 6-inch cake to 8-inch cake
- `milkbar_strawberry_shortcake.json`
  - Scaled from 6-inch cake to 8-inch cake
  - Jam: uses agar-agar for thickening

## JSON Format

Each recipe JSON includes:

```json
{
  "title": "Milkbar Carrot Graham Cake",
  "version": "v0.0.0",
  "components": [
    {
      "name": "Carrot Cake",
      "ingredients": [
        ["Butter, room temp", "230 g"],
        ["Light brown sugar", "240 g"]
        // ...
      ],
      "instructions": [
        "Heat the oven to 350°F.",
        "Combine the butter and sugars..."
      ]
    }
  ]
}
```

- **title**: Display name for the PDF.
- **version**: Version string to track edits.
- **components**: Each has a name, ingredient list, and step-by-step instructions.

## Setup & PDF Generation

### Create a virtual environment

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install reportlab
```

#### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install reportlab
```

### Generate a PDF

```bash
python3 recipe-card-from-json.py              \
  --json json/milkbar_carrot_graham_cake.json \
  --output pdf/milkbar_carrot_graham_cake.pdf
```

## Attribution

This project was developed with the assistance of [ChatGPT (OpenAI GPT-5)](https://openai.com/).

## License

- Copyright (c) 2025 Vincent Lucarelli
- This project is licensed under the [MIT License](LICENSE).
- You are free to use, modify, and distribute this software under the terms of that license.
