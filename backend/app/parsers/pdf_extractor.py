"""Extract text from PDF files (lease, PMA) using PyMuPDF."""
import base64
import logging

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text content from a PDF file.

    For text-based PDFs, uses PyMuPDF's embedded text extraction.
    For scanned/image-based PDFs (no embedded text), falls back to
    sending page images to Claude's vision API.

    Args:
        pdf_bytes: Raw bytes of the PDF file

    Returns:
        Extracted text as a single string with pages separated by newlines.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages.append(text.strip())
    doc.close()
    full_text = "\n\n".join(pages)

    if len(full_text.strip()) >= 100:
        return full_text

    # Scanned PDF — try Claude vision fallback
    logger.info("PDF appears scanned (%d chars extracted). Attempting vision-based extraction.", len(full_text.strip()))
    try:
        return _extract_text_via_vision(pdf_bytes)
    except Exception as exc:
        logger.warning("Vision-based PDF extraction failed: %s", exc)

    return full_text


def _extract_text_via_vision(pdf_bytes: bytes) -> str:
    """Extract text from a scanned PDF by sending page images to Claude vision API."""
    import anthropic

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_to_process = min(len(doc), 10)
    page_images = []
    for i in range(pages_to_process):
        page = doc[i]
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        page_images.append(base64.standard_b64encode(img_bytes).decode("utf-8"))
    doc.close()

    if not page_images:
        return ""

    client = anthropic.Anthropic()
    content: list = []
    for img_b64 in page_images:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
        })
    content.append({
        "type": "text",
        "text": (
            "Extract all text from these document pages. "
            "Return the raw text content only, preserving structure and formatting. "
            "Do not add any commentary."
        ),
    })

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": content}],
    )
    return response.content[0].text


def extract_text_from_pdf_file(file_path: str) -> str:
    """Extract text from a PDF file path."""
    with open(file_path, "rb") as f:
        return extract_text_from_pdf(f.read())
