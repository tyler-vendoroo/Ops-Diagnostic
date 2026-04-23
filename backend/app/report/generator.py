"""Report generator: Jinja2 template rendering + PDF generation.

Uses multiple strategies for HTML→PDF:
1. Playwright (local dev, best quality)
2. Subprocess Chromium/Chrome (works in any thread, any Python version)
3. pyppeteer as last resort
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import logging

from jinja2 import Environment, FileSystemLoader

from app.models.report_data import ReportData
from app.report.consistency import validate_report_consistency

logger = logging.getLogger(__name__)


TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_html(report_data: ReportData) -> str:
    """Render the report HTML from the Jinja2 template."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,
    )
    template = env.get_template("report.html")
    return template.render(r=report_data)


def _find_chrome_binary() -> str | None:
    """Find a Chrome/Chromium binary on the system."""
    candidates = [
        # Streamlit Cloud / Linux
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        # pyppeteer's downloaded Chromium
        os.path.expanduser("~/.local/share/pyppeteer/local-chromium/"),
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]

    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    # Check pyppeteer's download directory
    pyppeteer_dir = os.path.expanduser("~/.local/share/pyppeteer/local-chromium/")
    if os.path.isdir(pyppeteer_dir):
        for root, dirs, files in os.walk(pyppeteer_dir):
            for f in files:
                if f in ("chrome", "chromium", "headless_shell"):
                    full = os.path.join(root, f)
                    if os.access(full, os.X_OK):
                        return full

    # Try which/where
    for name in ["chromium", "chromium-browser", "google-chrome", "google-chrome-stable"]:
        path = shutil.which(name)
        if path:
            return path

    return None


def _ensure_pyppeteer_chromium() -> str | None:
    """Download Chromium via pyppeteer if not already present, return path."""
    try:
        from pyppeteer.chromium_downloader import download_chromium, chromium_executable
        if not os.path.exists(chromium_executable()):
            download_chromium()
        exe = chromium_executable()
        if os.path.exists(exe):
            return str(exe)
    except Exception:
        pass
    return None


def _generate_pdf_subprocess(html: str) -> bytes:
    """Generate PDF by calling Chrome/Chromium as a subprocess.

    This is the most reliable method — no async, no threads, no signals.
    Works in Streamlit Cloud, Jupyter, any Python version.
    """
    chrome = _find_chrome_binary()
    if not chrome:
        chrome = _ensure_pyppeteer_chromium()
    if not chrome:
        raise RuntimeError("No Chrome/Chromium binary found")

    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = os.path.join(tmpdir, "report.html")
        pdf_path = os.path.join(tmpdir, "report.pdf")

        with open(html_path, "w") as f:
            f.write(html)

        cmd = [
            chrome,
            "--headless",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--run-all-compositor-stages-before-draw",
            "--print-to-pdf=" + pdf_path,
            "--print-to-pdf-no-header",
            "--no-pdf-header-footer",
            f"file://{html_path}",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=60,
        )

        if not os.path.exists(pdf_path):
            raise RuntimeError(
                f"Chrome PDF generation failed. "
                f"stderr: {result.stderr.decode('utf-8', errors='replace')[:500]}"
            )

        with open(pdf_path, "rb") as f:
            return f.read()


def _generate_pdf_playwright(html: str) -> bytes:
    """Generate PDF using Playwright (preferred for local dev)."""
    import asyncio
    from playwright.async_api import async_playwright

    async def _run():
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html, wait_until="networkidle")
            pdf_bytes = await page.pdf(
                format="Letter",
                print_background=True,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            )
            await browser.close()
        return pdf_bytes

    return asyncio.run(_run())


def generate_pdf(report_data: ReportData) -> bytes:
    """Generate a branded PDF from the HTML template.

    Requires Playwright or Chrome/Chromium. Raises RuntimeError if neither
    is available. The ReportLab fallback has been removed — it produced
    hardcoded sample data unfit for real prospects.
    """
    mismatches = validate_report_consistency(report_data)
    if mismatches:
        logger.warning("Report consistency warnings (not blocking): %s", "; ".join(mismatches))

    html = render_html(report_data)

    try:
        return _generate_pdf_playwright(html)
    except Exception as playwright_exc:
        playwright_error = str(playwright_exc)

    try:
        return _generate_pdf_subprocess(html)
    except Exception as chrome_exc:
        chrome_error = str(chrome_exc)

    raise RuntimeError(
        f"PDF generation requires Playwright or Chrome/Chromium. "
        f"Playwright: {playwright_error}. Chrome: {chrome_error}"
    )


def generate_html_preview(report_data: ReportData) -> str:
    """Generate HTML for browser preview."""
    return render_html(report_data)
