import io
import logging
import warnings
import pypdf

logging.getLogger("pypdf").setLevel(logging.ERROR)


class PDFExtractor:
    def __init__(self, pdf_bytes: bytes):
        self.pdf_bytes = pdf_bytes

    def extract_text(self, max_pages: int | None = None) -> str:
        if not pypdf or not self.pdf_bytes:
            return ""

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")

                reader = pypdf.PdfReader(io.BytesIO(self.pdf_bytes), strict=False)
                if not reader.pages:
                    return ""

                pages = reader.pages[:max_pages] if max_pages else reader.pages
                extracted = [page.extract_text() or "" for page in pages]

                return "\n".join(extracted).strip()
        except Exception:
            return ""

    def extract_first_page(self) -> str:
        return self.extract_text(max_pages=1)

    def extract_last_page(self) -> str:
        reader = pypdf.PdfReader(io.BytesIO(self.pdf_bytes))
        if len(reader.pages) > 0:
            return reader.pages[-1].extract_text() or ""
        return ""
