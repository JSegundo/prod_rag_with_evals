import tiktoken

from app.pipeline.extractor import ExtractionResult


class TextChunker:
    def __init__(self, max_tokens: int = 1500, overlap_tokens: int = 200):
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.max_tokens = max_tokens
        self.overlap = overlap_tokens
        self.separators = ["\n\n", "\n", ". ", " "]

    def chunk(self, extraction: ExtractionResult) -> list[dict]:
        """Split extracted text into token-limited chunks with page tracking."""
        # Build a map of character offset -> page number
        page_map = self._build_page_map(extraction.pages)

        text = extraction.text
        if not text.strip():
            return []

        raw_chunks = self._recursive_split(text)

        # Assign page numbers and build output
        result = []
        offset = 0
        for chunk_text in raw_chunks:
            # Find this chunk's position in the original text
            idx = text.find(chunk_text, offset)
            if idx == -1:
                idx = offset

            page_numbers = self._get_page_numbers(idx, idx + len(chunk_text), page_map)
            result.append({
                "text": chunk_text.strip(),
                "page_numbers": page_numbers,
                "metadata": {},
            })
            offset = idx + len(chunk_text) - (self.overlap * 4)  # approximate char overlap

        return [c for c in result if c["text"]]

    def _recursive_split(self, text: str) -> list[str]:
        """Recursively split text to fit within max_tokens."""
        tokens = self.encoder.encode(text)
        if len(tokens) <= self.max_tokens:
            return [text] if text.strip() else []

        # Try each separator
        for sep in self.separators:
            parts = text.split(sep)
            if len(parts) == 1:
                continue

            chunks = []
            current = ""
            for part in parts:
                candidate = current + sep + part if current else part
                if len(self.encoder.encode(candidate)) <= self.max_tokens:
                    current = candidate
                else:
                    if current:
                        chunks.append(current)
                    # If this single part is too large, recurse
                    if len(self.encoder.encode(part)) > self.max_tokens:
                        chunks.extend(self._recursive_split(part))
                        current = ""
                    else:
                        current = part

            if current:
                chunks.append(current)

            # Add overlap between chunks
            if self.overlap > 0 and len(chunks) > 1:
                chunks = self._add_overlap(chunks)

            return chunks

        # Fallback: hard split by tokens
        return self._token_split(text)

    def _token_split(self, text: str) -> list[str]:
        """Hard split by token count as a last resort."""
        tokens = self.encoder.encode(text)
        chunks = []
        start = 0
        while start < len(tokens):
            end = min(start + self.max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunks.append(self.encoder.decode(chunk_tokens))
            start = end - self.overlap if end < len(tokens) else end
        return chunks

    def _add_overlap(self, chunks: list[str]) -> list[str]:
        """Add token overlap between consecutive chunks."""
        if len(chunks) <= 1:
            return chunks

        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tokens = self.encoder.encode(chunks[i - 1])
            overlap_text = self.encoder.decode(prev_tokens[-self.overlap:])
            result.append(overlap_text + chunks[i])
        return result

    def _build_page_map(self, pages: list[dict]) -> list[tuple[int, int, int]]:
        """Build a list of (start_char, end_char, page_number) from pages."""
        page_map = []
        offset = 0
        for page in pages:
            text = page["text"]
            if text.strip():
                page_map.append((offset, offset + len(text), page["page_number"]))
                offset += len(text) + 2  # +2 for the \n\n join
            else:
                offset += 2
        return page_map

    def _get_page_numbers(
        self, start: int, end: int, page_map: list[tuple[int, int, int]]
    ) -> list[int]:
        """Find which pages a character range spans."""
        pages = set()
        for pstart, pend, pnum in page_map:
            if start < pend and end > pstart:
                pages.add(pnum)
        return sorted(pages) if pages else [1]
