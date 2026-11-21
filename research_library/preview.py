"""Render one physical page using the PDFium library."""

import io
import math
from threading import Lock

import pypdfium2 as pdfium

_PDFIUM_LOCK = Lock()


def render_page_png(raw, number):
    # PDFium is not thread-safe even when rendering different documents.
    with _PDFIUM_LOCK:
        with pdfium.PdfDocument(raw) as original:
            page = original[number - 1]
            try:
                width, height = page.get_size()
                if not all(math.isfinite(value) and value > 0 for value in (width, height)):
                    raise ValueError("Invalid PDF page dimensions")
                scale = min(1.55, 1250 / max(width, height))
                bitmap = page.render(scale=scale)
                try:
                    png = io.BytesIO()
                    image = bitmap.to_pil()
                    try:
                        image.save(png, format="PNG")
                    finally:
                        image.close()
                    png.seek(0)
                    return png
                finally:
                    bitmap.close()
            finally:
                page.close()
