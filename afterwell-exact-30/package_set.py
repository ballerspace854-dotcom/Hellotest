#!/usr/bin/env python3
"""Validate and package the completed 30-ad set without changing final artwork.

Run only after rendering all ads: python package_set.py
Validation only: python package_set.py --check-only
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import math
from pathlib import Path
import re
import tempfile
from urllib.parse import quote
import zipfile

from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent
REPOSITORY_URL = "https://github.com/ballerspace854-dotcom/Hellotest/tree/main/afterwell-exact-30"
ZIP_NAME = "afterwell-exact-30.zip"
EXPECTED_IDS = set(range(1, 31))
SIZE = (1080, 1350)
NAVY = "#1E2A5A"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
CSV_FIELDS = [
    "ad_number", "angle", "headline", "support", "footnote", "headline_words",
    "support_words", "filename", "width", "height", "byte_size", "sha256",
    "scene_asset", "product_asset", "logo_asset", "editable", "source_record",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_inputs(root: Path) -> list[dict]:
    """Read all inputs before creating any package or preview files."""
    image_dir = root / "statics"
    images = sorted(p for p in image_dir.iterdir() if p.is_file() and p.suffix.lower() == ".png") if image_dir.exists() else []
    if len(images) != 30:
        raise ValueError(f"Expected exactly 30 final PNGs in statics/; found {len(images)}. Finish all renders first.")
    record_paths = sorted((root / "source").glob("ad-*.json"))
    expected_names = {f"ad-{number:02}.json" for number in EXPECTED_IDS}
    if {p.name for p in record_paths} != expected_names:
        missing = sorted(expected_names - {p.name for p in record_paths})
        extra = sorted({p.name for p in record_paths} - expected_names)
        raise ValueError(f"Source records must be exactly ad-01.json through ad-30.json; missing={missing}, extra={extra}")
    for asset in ("product-master.png", "afterwell-logo-blue.png"):
        if not (root / "assets" / asset).is_file():
            raise ValueError(f"Missing fixed asset: assets/{asset}")
    if not (root / "source" / "updated-creative-brief.txt").is_file():
        raise ValueError("Missing latest brief: source/updated-creative-brief.txt")

    rows = []
    seen_ids = set()
    seen_filenames = set()
    for path in record_paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        number = record.get("ad_number")
        if type(number) is not int or number not in EXPECTED_IDS or number in seen_ids:
            raise ValueError(f"Invalid or repeated ad_number in {path.name}: {number!r}")
        if path.name != f"ad-{number:02}.json":
            raise ValueError(f"Record filename and ad_number disagree: {path.name}")
        seen_ids.add(number)
        filename = record.get("filename", "")
        if not isinstance(filename, str) or Path(filename).name != filename or not re.fullmatch(rf"{number:02}-[a-z0-9-]+\.png", filename):
            raise ValueError(f"Invalid PNG filename for ad {number:02}: {filename!r}")
        if filename in seen_filenames:
            raise ValueError(f"Duplicate PNG reference: {filename}")
        seen_filenames.add(filename)
        image_path = image_dir / filename
        if not image_path.is_file():
            raise ValueError(f"Missing final PNG: statics/{filename}")
        with Image.open(image_path) as im:
            if im.format != "PNG" or im.size != SIZE:
                raise ValueError(f"{filename}: expected a 1080 × 1350 PNG, found {im.format} {im.size}")
            im.verify()
        headline = record.get("headline", "")
        support = record.get("support", "")
        if not isinstance(headline, str) or not 3 <= len(headline.split()) <= 8:
            raise ValueError(f"Ad {number:02} headline must have 3–8 words: {headline!r}")
        if not isinstance(support, str) or not 1 <= len(support.split()) <= 12:
            raise ValueError(f"Ad {number:02} support must have 1–12 words: {support!r}")
        if record.get("dimensions") != list(SIZE):
            raise ValueError(f"Ad {number:02} metadata dimensions must be [1080, 1350]")
        if record.get("product_asset") != "product-master.png":
            raise ValueError(f"Ad {number:02} must reference the one fixed product-master.png")
        if record.get("logo_asset") != "afterwell-logo-blue.png":
            raise ValueError(f"Ad {number:02} must reference the separate official blue footer mark")
        rows.append({
            **record,
            "width": SIZE[0], "height": SIZE[1],
            "headline_words": len(headline.split()), "support_words": len(support.split()),
            "byte_size": image_path.stat().st_size, "sha256": sha256(image_path),
            "source_record": f"source/{path.name}",
            "footnote": record.get("footnote", ""),
        })
    if seen_ids != EXPECTED_IDS or seen_filenames != {p.name for p in images}:
        raise ValueError("The final PNGs and source records must map one-to-one to IDs 01–30")
    return sorted(rows, key=lambda row: row["ad_number"])


def png_link(row: dict) -> str:
    return "statics/" + quote(row["filename"])


def write_copy_indexes(output: Path, rows: list[dict]) -> None:
    payload = {
        "count": 30, "dimensions": list(SIZE),
        "brief": "source/updated-creative-brief.txt",
        "brief_note": "The updated brief supersedes source/creative-brief.txt.",
        "ads": rows,
    }
    (output / "copy-index.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (output / "copy-index.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_gallery(output: Path, rows: list[dict]) -> None:
    cards = []
    for row in rows:
        number = row["ad_number"]
        headline, support = html.escape(row["headline"]), html.escape(row["support"])
        foot = f'<p class="footnote">{html.escape(row["footnote"])}</p>' if row["footnote"] else ""
        label = f'Ad {number:02}: {row["headline"]}. {row["support"]}'
        src = html.escape(png_link(row), quote=True)
        cards.append(f'''<figure id="ad-{number:02}">
  <a class="image-link" href="{src}" aria-label="Open full-size {html.escape(label, quote=True)}"><img src="{src}" width="1080" height="1350" loading="lazy" alt="{html.escape(label, quote=True)}"></a>
  <figcaption><p class="number">AD {number:02} · {html.escape(row.get('angle', ''))}</p><h2>{headline}</h2><p>{support}</p>{foot}<a class="download" href="{src}" download>Download ad {number:02} PNG <span class="file-size">({row['byte_size'] / 1024 / 1024:.1f} MB)</span></a></figcaption>
</figure>''')
    document = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Afterwell · 30-ad gallery</title>
<style>
:root{color-scheme:light;font:16px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#18264d;background:#f2f6fa}*{box-sizing:border-box}body{margin:0}a{color:#1e2a5a;text-underline-offset:3px}a:focus-visible{outline:3px solid #cf5a08;outline-offset:5px}.skip{position:absolute;left:16px;top:-80px;background:white;padding:8px;z-index:2}.skip:focus{top:12px}header,main,footer{max-width:1560px;margin:auto;padding:28px}header{padding-bottom:12px}h1{font-size:clamp(1.8rem,4vw,2.7rem);line-height:1.15;margin:.2em 0}.intro{max-width:850px}nav{display:flex;gap:12px 24px;flex-wrap:wrap;margin:20px 0}nav a{font-weight:650}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:24px}figure{margin:0;background:white;border:1px solid #cbd7e2;border-radius:10px;overflow:hidden;box-shadow:0 4px 12px #18264d08}.image-link{display:block}img{display:block;width:100%;height:auto;aspect-ratio:4/5}figcaption{padding:18px}.number{font-size:.8rem;letter-spacing:.03em;color:#465774;margin:0 0 6px}h2{font-size:1.12rem;line-height:1.3;margin:0 0 8px}figcaption p{margin:0 0 12px}.footnote,.file-size{font-size:.85rem}.download{display:inline-block;font-weight:650}footer{font-size:.9rem;padding-top:10px;padding-bottom:36px}footer p{max-width:1000px}
</style></head><body><a class="skip" href="#gallery">Skip to all 30 ads</a>
<header><p>AFTERWELL · CREATIVE REVIEW</p><h1>All 30 ads. Full size.</h1><p class="intro">Each final PNG is 1080 × 1350 pixels. Choose an image to view it full size, or use its download link. The final PNGs are included unchanged in the ZIP.</p>
<nav aria-label="Set downloads"><a href="contact-sheet.pdf" download>Contact sheet PDF</a><a href="copy-index.csv" download>Copy index CSV</a><a href="copy-index.json" download>Copy index JSON</a><a href="sources.md">Source notes</a></nav></header>
<main id="gallery" class="grid" aria-label="All 30 final ads">''' + "\n".join(cards) + '''</main>
<footer><p>New scenes are AI-generated illustrations. People shown are not customers, and images do not show clinical results. One fixed isolated product master retains the original physical label, including “THE OCEAN HEALED MY ECZEMA”; the official Afterwell mark is recolored blue and placed separately in the footer. See source notes for production details.</p><p>The editable SVGs and supporting assets are available separately in the <a href="''' + REPOSITORY_URL + '''">project repository</a>.</p></footer></body></html>
'''
    (output / "index.html").write_text(document, encoding="utf-8")


def wrap_pdf(text: str, font: str, size: float, width: float) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and pdfmetrics.stringWidth(candidate, font, size) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def write_pdf(root: Path, output: Path, rows: list[dict]) -> None:
    pdfmetrics.registerFont(TTFont("AfterwellRegular", str(FONT_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("AfterwellBold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
    page_w, page_h = A4
    margin, gap = 24, 14
    top, bottom = page_h - 53, 29
    cell_w, cell_h = (page_w - 2 * margin - gap) / 2, (top - bottom - gap) / 2
    doc = canvas.Canvas(str(output / "contact-sheet.pdf"), pagesize=A4, pageCompression=1)
    doc.setTitle("Afterwell · 30-ad contact sheet")
    doc.setAuthor("Afterwell creative production")
    doc.setSubject("30 final ads at four per page; AI-generated illustrative scenes")
    for start in range(0, len(rows), 4):
        doc.setFillColor(HexColor(NAVY))
        doc.setFont("AfterwellBold", 14)
        doc.drawString(margin, page_h - 29, "AFTERWELL · ALL 30 ADS")
        doc.setFont("AfterwellRegular", 8)
        doc.drawRightString(page_w - margin, page_h - 28, f"{start // 4 + 1} / {math.ceil(len(rows) / 4)}")
        for offset, row in enumerate(rows[start:start + 4]):
            col, line = offset % 2, offset // 2
            x, y_top = margin + col * (cell_w + gap), top - line * (cell_h + gap)
            doc.setStrokeColor(HexColor("#d2dce6"))
            doc.setFillColor(HexColor("#ffffff"))
            doc.roundRect(x, y_top - cell_h, cell_w, cell_h, 5, fill=1, stroke=1)
            doc.setFillColor(HexColor(NAVY))
            doc.setFont("AfterwellBold", 8)
            doc.drawString(x + 11, y_top - 15, f"AD {row['ad_number']:02}")
            # The PDF uses a compact preview; the downloaded final PNG stays untouched.
            image_h = cell_h - 99
            image_w = image_h * 4 / 5
            image_x, image_y = x + (cell_w - image_w) / 2, y_top - 25 - image_h
            with Image.open(root / "statics" / row["filename"]) as original:
                preview = original.convert("RGB")
                preview.thumbnail((540, 675), Image.Resampling.LANCZOS)
                encoded = io.BytesIO()
                preview.save(encoded, format="JPEG", quality=88, subsampling=0)
            encoded.seek(0)
            doc.drawImage(ImageReader(encoded), image_x, image_y, image_w, image_h)
            text_y = image_y - 12
            doc.setFillColor(HexColor(NAVY))
            doc.setFont("AfterwellBold", 8.5)
            for text_line in wrap_pdf(row["headline"], "AfterwellBold", 8.5, cell_w - 22):
                doc.drawString(x + 11, text_y, text_line)
                text_y -= 10.5
            text_y -= 2
            doc.setFont("AfterwellRegular", 7.6)
            for text_line in wrap_pdf(row["support"], "AfterwellRegular", 7.6, cell_w - 22):
                doc.drawString(x + 11, text_y, text_line)
                text_y -= 9.5
            if row["footnote"]:
                doc.setFont("AfterwellRegular", 6.7)
                for text_line in wrap_pdf(row["footnote"], "AfterwellRegular", 6.7, cell_w - 22):
                    doc.drawString(x + 11, text_y, text_line)
                    text_y -= 8
            if text_y < y_top - cell_h + 4:
                raise ValueError(f"Contact sheet caption would overflow for ad {row['ad_number']:02}")
        doc.setFillColor(HexColor("#465774"))
        doc.setFont("AfterwellRegular", 6.5)
        doc.drawString(margin, 15, "AI-generated illustrative scenes; not customers or clinical results. Final files: statics/ · Copy: copy-index.csv")
        doc.showPage()
    doc.save()


def wrap_image(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and font.getlength(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    return lines + ([current] if current else [])


def write_overview(root: Path, output: Path, rows: list[dict]) -> None:
    columns, card_w, card_h, gap, margin, header = 5, 320, 510, 18, 30, 98
    width = margin * 2 + columns * card_w + (columns - 1) * gap
    height = header + 6 * card_h + 5 * gap + margin + 30
    sheet = Image.new("RGB", (width, height), "#edf3f8")
    draw = ImageDraw.Draw(sheet)
    bold = ImageFont.truetype(str(FONT_DIR / "DejaVuSans-Bold.ttf"), 15)
    regular = ImageFont.truetype(str(FONT_DIR / "DejaVuSans.ttf"), 12)
    title = ImageFont.truetype(str(FONT_DIR / "DejaVuSans-Bold.ttf"), 30)
    draw.text((margin, 22), "AFTERWELL · ALL 30 ADS", font=title, fill=NAVY)
    draw.text((margin, 65), "1080 × 1350 final PNGs · Numbered 01–30 · See contact-sheet.pdf for larger previews", font=regular, fill="#465774")
    for index, row in enumerate(rows):
        x = margin + (index % columns) * (card_w + gap)
        y = header + (index // columns) * (card_h + gap)
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=7, fill="white", outline="#cbd7e2")
        with Image.open(root / "statics" / row["filename"]) as original:
            preview = ImageOps.contain(original.convert("RGB"), (300, 375), Image.Resampling.LANCZOS)
            sheet.paste(preview, (x + (card_w - preview.width) // 2, y + 10))
        caption_y = y + 397
        caption = f"{row['ad_number']:02} · {row['headline']}"
        for line in wrap_image(caption, bold, card_w - 20):
            draw.text((x + 10, caption_y), line, font=bold, fill=NAVY)
            caption_y += 20
        for line in wrap_image(row["support"], regular, card_w - 20):
            draw.text((x + 10, caption_y + 2), line, font=regular, fill="#465774")
            caption_y += 17
        if caption_y > y + card_h - 8:
            raise ValueError(f"Overview caption would overflow for ad {row['ad_number']:02}")
    draw.text((margin, height - 27), "AI-generated illustrative scenes; people shown are not customers, and images do not show clinical results.", font=regular, fill="#465774")
    sheet.save(output / "contact-sheet.jpg", quality=92, subsampling=0, optimize=True)


def write_notes(root: Path, output: Path, rows: list[dict]) -> None:
    source_notes = f'''# Sources and production notes

This set contains exactly 30 final static ads, numbered 01–30, at 1080 × 1350 pixels.

- The governing copy brief is `source/updated-creative-brief.txt`, which supersedes `source/creative-brief.txt`. Headline length is 3–8 words; support length is at most 12 words. Individual production records are in `source/ad-01.json` through `source/ad-30.json`; the packaged copy indexes preserve their text and references.
- The supplied product reference was isolated with an image-edit tool to create one fixed `assets/product-master.png`. Every ad uses that same product master. Its original physical label is retained, including **THE OCEAN HEALED MY ECZEMA** (and the source label's asterisk). The original label is not rewritten or relabeled with Afterwell. Isolation is an edited asset workflow; this is not a claim that the product is a pixel-identical passthrough of the original uploaded file.
- The supplied official Afterwell wordmark was isolated/recolored blue as `assets/afterwell-logo-blue.png`. It appears separately as the small footer mark. It is not placed on the jar label.
- New people, skin details, rooms and still-life scenes were created with AI image tools as illustrative creative. People shown are not customers. These are not testimonials, clinical photographs, before/after evidence, or clinical results.
- Layout and text are editable SVG compositions rendered with Inkscape. Packaging and previews use Python, Pillow and ReportLab. Packaging copies the final PNG bytes unchanged; resizing and JPEG compression apply only to contact-sheet previews.
- The archive includes the 30 final PNGs, `index.html`, `copy-index.csv`, `copy-index.json`, `sources.md` and `contact-sheet.pdf`. Editable SVGs, linked image assets, full production records, briefs and the JPG overview remain available separately in the [repository]({REPOSITORY_URL}). Open the extracted `index.html` in a browser for the complete gallery.

Fixed asset fingerprints at packaging time:

| Asset | SHA-256 |
| --- | --- |
| `assets/product-master.png` | `{sha256(root / 'assets' / 'product-master.png')}` |
| `assets/afterwell-logo-blue.png` | `{sha256(root / 'assets' / 'afterwell-logo-blue.png')}` |

Each final PNG's SHA-256 and byte size are recorded in `copy-index.json` and `copy-index.csv`. Automated packaging checks verify dimensions, file/record counts, sequential IDs, copy lengths, and fixed asset references in metadata. Visual approval of the artwork remains a separate review.
'''
    (output / "sources.md").write_text(source_notes, encoding="utf-8")
    lines = [
        "# Afterwell · exact 30-ad set", "",
        "30 final PNGs, numbered 01–30. Each is **1080 × 1350** pixels.", "",
        f"[Download the complete ZIP]({ZIP_NAME}) · [Individual PNG folder](statics/) · [Contact sheet PDF](contact-sheet.pdf) · [Overview JPG](contact-sheet.jpg)", "",
        "[Browser gallery](index.html) · [Copy CSV](copy-index.csv) · [Copy JSON](copy-index.json) · [Source notes](sources.md) · [Editable SVGs](editable/)", "",
        "Download and extract the ZIP, then open `index.html` in your browser to view all 30 ads and download individual full-size PNGs. The ZIP contains the final PNGs, gallery, copy indexes, source notes and contact PDF. Editable SVGs and supporting assets are available separately in this repository.", "",
        "The original product label, including **THE OCEAN HEALED MY ECZEMA**, is retained on one fixed isolated product master. The supplied official Afterwell mark is blue and placed separately in the footer. New scenes are AI-generated illustrations; people shown are not customers, and images do not show clinical results. See [sources.md](sources.md) for the edited-asset workflow and full production notes.", "",
        "## Preview all 30", "",
        "Select any preview for its full-size PNG.", "", "<table>",
    ]
    for start in range(0, len(rows), 3):
        lines.append("<tr>")
        for row in rows[start:start + 3]:
            label = html.escape(f"{row['ad_number']:02} · {row['headline']}")
            src = html.escape(png_link(row), quote=True)
            lines.append(f'<td width="33%" valign="top"><a href="{src}"><img src="{src}" width="260" alt="{label}"></a><br><strong>{label}</strong><br>{html.escape(row["support"])}<br><a href="{src}">Download PNG {row["ad_number"]:02}</a></td>')
        lines.append("</tr>")
    lines += ["</table>", "", "## Rebuild the package", "", "After all 30 renders and source records exist, run `python package_set.py`. Use `python package_set.py --check-only` to validate inputs without writing outputs. Packaging requires Python, Pillow, ReportLab and DejaVu Sans fonts. It never resizes or recompresses the final PNGs.", ""]
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")


def build_archive(root: Path, output: Path, rows: list[dict]) -> None:
    archive_path = output / ZIP_NAME
    documents = ["index.html", "copy-index.csv", "copy-index.json", "sources.md", "contact-sheet.pdf"]
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for row in rows:
            archive.write(root / "statics" / row["filename"], f"statics/{row['filename']}")
        for filename in documents:
            archive.write(output / filename, filename)
    with zipfile.ZipFile(archive_path) as archive:
        bad_file = archive.testzip()
        if bad_file:
            raise ValueError(f"ZIP integrity check failed: {bad_file}")
        expected = {f"statics/{row['filename']}" for row in rows} | set(documents)
        if set(archive.namelist()) != expected:
            raise ValueError("ZIP members do not match the intended delivery set")
        for row in rows:
            with archive.open(f"statics/{row['filename']}") as handle:
                if hashlib.file_digest(handle, "sha256").hexdigest() != row["sha256"]:
                    raise ValueError(f"Archived PNG differs from its final source: {row['filename']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Completed set directory (default: this script's directory)")
    parser.add_argument("--check-only", action="store_true", help="Validate inputs without writing package files")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        rows = validate_inputs(root)
        total = sum(row["byte_size"] for row in rows)
        print(f"Validated all 30 PNGs and source records: IDs 01–30, 1080 × 1350, {total / 1024 / 1024:.1f} MiB total PNG data.")
        if args.check_only:
            return
        with tempfile.TemporaryDirectory(prefix=".packaging-", dir=root) as temp_dir:
            output = Path(temp_dir)
            write_copy_indexes(output, rows)
            write_gallery(output, rows)
            write_pdf(root, output, rows)
            write_overview(root, output, rows)
            write_notes(root, output, rows)
            build_archive(root, output, rows)
            for path in output.iterdir():
                path.replace(root / path.name)
        zip_mib = (root / ZIP_NAME).stat().st_size / 1024 / 1024
        print(f"Created gallery, copy indexes, 4-per-page PDF, 30-image JPG overview, README, source notes and ZIP ({zip_mib:.1f} MiB).")
        if zip_mib >= 50:
            print("NOTE: The ZIP exceeds 50 MiB. Final PNGs were preserved unchanged; no quality reduction was applied.")
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Packaging stopped: {exc}\n")


if __name__ == "__main__":
    main()
