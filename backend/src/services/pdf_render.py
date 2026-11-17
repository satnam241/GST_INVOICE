"""What a PDF being rendered may load.

Documents are built from tenant-supplied text, so a stray tag in one must not be able
to pull a server file or an internal URL into the PDF. Everything a template legitimately
embeds (logos, QR codes) is already a data: URI, so nothing else is ever fetched.
"""

try:
    from weasyprint.urls import default_url_fetcher
except (ImportError, OSError):
    default_url_fetcher = None


def safe_url_fetcher(url: str, *args, **kwargs):
    if url.startswith("data:"):
        if default_url_fetcher is not None:
            return default_url_fetcher(url, *args, **kwargs)
        return {"string": b""}
    raise ValueError("PDF rendering only loads data: URLs")
