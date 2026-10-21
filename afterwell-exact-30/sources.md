# Sources and production notes

This set contains exactly 30 final static ads, numbered 01–30, at 1080 × 1350 pixels.

- The governing copy brief is `source/updated-creative-brief.txt`, which supersedes `source/creative-brief.txt`. Headline length is 3–8 words; support length is at most 12 words. Individual production records are in `source/ad-01.json` through `source/ad-30.json`; the packaged copy indexes preserve their text and references.
- The supplied product reference was isolated with an image-edit tool to create one fixed `assets/product-master.png`. Every ad uses that same product master. Its original physical label is retained, including **THE OCEAN HEALED MY ECZEMA** (and the source label's asterisk). The original label is not rewritten or relabeled with Afterwell. Isolation is an edited asset workflow; this is not a claim that the product is a pixel-identical passthrough of the original uploaded file.
- The supplied official Afterwell wordmark was isolated/recolored blue as `assets/afterwell-logo-blue.png`. It appears separately as the small footer mark. It is not placed on the jar label.
- New people, skin details, rooms and still-life scenes were created with AI image tools as illustrative creative. People shown are not customers. These are not testimonials, clinical photographs, before/after evidence, or clinical results.
- Layout and text are editable SVG compositions rendered with Inkscape. Packaging and previews use Python, Pillow and ReportLab. Packaging copies the final PNG bytes unchanged; resizing and JPEG compression apply only to contact-sheet previews.
- The archive includes the 30 final PNGs, `index.html`, `copy-index.csv`, `copy-index.json`, `sources.md` and `contact-sheet.pdf`. Editable SVGs, linked image assets, full production records, briefs and the JPG overview remain available separately in the [repository](https://github.com/ballerspace854-dotcom/Hellotest/tree/main/afterwell-exact-30). Open the extracted `index.html` in a browser for the complete gallery.

Fixed asset fingerprints at packaging time:

| Asset | SHA-256 |
| --- | --- |
| `assets/product-master.png` | `4a1dd84f628b64d22460825263d30d322474837d3e7dccef441c9ef9b834134d` |
| `assets/afterwell-logo-blue.png` | `1aca8dd1774e57548ede29d592be2f689e23ffec3dff3ac91eb719a0c6620a1d` |

Each final PNG's SHA-256 and byte size are recorded in `copy-index.json` and `copy-index.csv`. Automated packaging checks verify dimensions, file/record counts, sequential IDs, copy lengths, and fixed asset references in metadata. Visual approval of the artwork remains a separate review.
