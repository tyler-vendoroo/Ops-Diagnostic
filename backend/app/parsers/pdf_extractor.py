"""Extract text from PDF files (lease, PMA) using PyMuPDF."""
import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text content from a PDF file.

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
    return "\n\n".join(pages)


def extract_text_from_pdf_file(file_path: str) -> str:
    """Extract text from a PDF file path."""
    with open(file_path, "rb") as f:
        return extract_text_from_pdf(f.read())
