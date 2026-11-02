"""Render the real offline CLI export as a portfolio preview; run from the repo root."""

import csv
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main():
    output = Path("out/preview.csv")
    subprocess.run(
        [sys.executable, "-m", "leadlist", "--city", "X", "--type", "bakery",
         "--offline", "tests/fixtures/overpass_sample.json", "--out", str(output)],
        check=True,
    )
    with output.open(encoding="utf-8", newline="") as stream:
        header, *rows = list(csv.reader(stream))

    image = Image.new("RGB", (1800, 740), "#f3f5f8")
    draw = ImageDraw.Draw(image)
    title = ImageFont.load_default(size=44)
    label = ImageFont.load_default(size=22)
    body = ImageFont.load_default(size=18)
    small = ImageFont.load_default(size=16)

    draw.rectangle((0, 0, 1800, 205), fill="#112b40")
    draw.text((70, 30), "PUBLIC DATA / PYTHON + AGENT SKILL", font=small, fill="#72deca")
    draw.text((70, 65), "Business list, ready for a spreadsheet.", font=title, fill="white")
    draw.text((70, 135), "A real CLI export from fictional offline data. No API key required.",
              font=label, fill="#d3e1eb")

    for x, value, caption in (
        (70, str(len(rows)), "sorted, unique businesses"),
        (630, str(len(header)), "CSV columns"),
        (1190, "OFFLINE", "reproducible fixture export"),
    ):
        draw.rounded_rectangle((x, 235, x + 540, 335), radius=12, fill="white")
        draw.text((x + 22, 250), value, font=label, fill="#087b6b")
        draw.text((x + 22, 290), caption, font=body, fill="#405369")

    widths = [220, 110, 210, 100, 100, 265, 655]
    draw.rounded_rectangle((70, 370, 1730, 655), radius=12, fill="white")
    draw.rectangle((70, 370, 1730, 420), fill="#dce8f0")
    for index, row in enumerate([header, *rows]):
        y = 385 if index == 0 else 442 + (index - 1) * 54
        x = 85
        for value, width in zip(row, widths):
            draw.text((x, y), value, font=small, fill="#172f44")
            x += width
        if index > 0:
            draw.line((85, y + 35, 1715, y + 35), fill="#e4eaf0")

    draw.text((70, 690), "preview.csv  |  sorted by name  |  duplicates removed  |  empty fields preserved",
              font=body, fill="#405369")
    preview = Path("docs/preview.png")
    image.save(preview)
    print(f"Rendered {len(rows)} businesses to {preview} ({preview.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
