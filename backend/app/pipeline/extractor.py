import os
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ExtractionResult:
    text: str
    pages: list[dict]  # [{"page_number": int, "text": str}]


class ExtractorBase(ABC):
    @abstractmethod
    def extract(self, file_path: str) -> ExtractionResult:
        ...


class PdfPlumberExtractor(ExtractorBase):
    def extract(self, file_path: str) -> ExtractionResult:
        import pdfplumber

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        pages = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                tables = page.extract_tables()
                table_text = self._tables_to_markdown(tables)

                full_page_text = text
                if table_text:
                    full_page_text += "\n\n" + table_text

                pages.append({"page_number": i + 1, "text": full_page_text})

        full_text = "\n\n".join(p["text"] for p in pages if p["text"].strip())
        return ExtractionResult(text=full_text, pages=pages)

    def _tables_to_markdown(self, tables: list) -> str:
        if not tables:
            return ""

        md_tables = []
        for table in tables:
            if not table or not table[0]:
                continue
            # Header row
            header = "| " + " | ".join(str(cell or "") for cell in table[0]) + " |"
            separator = "| " + " | ".join("---" for _ in table[0]) + " |"
            rows = []
            for row in table[1:]:
                rows.append("| " + " | ".join(str(cell or "") for cell in row) + " |")
            md_tables.append("\n".join([header, separator] + rows))

        return "\n\n".join(md_tables)


class DoclingExtractor(ExtractorBase):
    def __init__(self):
        try:
            from docling.document_converter import DocumentConverter
            self.converter = DocumentConverter()
        except ImportError:
            raise ImportError(
                "Docling is not installed. Install with: pip install -r requirements-docling.txt"
            )

    def extract(self, file_path: str) -> ExtractionResult:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        result = self.converter.convert(file_path)
        document = result.document
        markdown_output = document.export_to_markdown()

        # Build page-level data from the markdown
        # Docling doesn't give us clean per-page splits, so we treat the whole doc as one
        pages = [{"page_number": 1, "text": markdown_output}]

        return ExtractionResult(text=markdown_output, pages=pages)


def create_extractor(extractor_type: str = "pdfplumber") -> ExtractorBase:
    if extractor_type == "docling":
        return DoclingExtractor()
    return PdfPlumberExtractor()
