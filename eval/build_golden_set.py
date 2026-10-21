#!/usr/bin/env python3
"""Build eval/golden_set.json from a local FinanceBench clone.

Usage:
    python3 eval/build_golden_set.py <path-to-financebench-clone> [doc_name ...]

With no doc_name args, includes every question in the dataset (all 84
referenced docs). Pass doc_names to scope it to a subset you've actually
ingested (see eval/financebench/pdfs/ for what's currently ingested).
"""
import json
import sys
from pathlib import Path


def main() -> None:
    repo = Path(sys.argv[1])
    allowed = set(sys.argv[2:]) or None

    rows = [
        json.loads(line)
        for line in (repo / "data" / "financebench_open_source.jsonl").open()
    ]

    golden = []
    for r in rows:
        if allowed is not None and r["doc_name"] not in allowed:
            continue
        evidence = r["evidence"][0]
        golden.append(
            {
                "id": r["financebench_id"],
                "question": r["question"],
                "expected_answer": r["answer"],
                "expected_source_doc": r["doc_name"],
                # FinanceBench's evidence_page_num is 0-indexed (pdfplumber's native
                # index); this app's extractor.py stores page_number as i + 1. +1 here
                # keeps golden-set pages comparable to chunks.page_numbers in the DB.
                "expected_page": evidence["evidence_page_num"] + 1,
            }
        )

    out = Path(__file__).parent / "golden_set.json"
    out.write_text(json.dumps(golden, indent=2, ensure_ascii=False) + "\n")
    docs = {g["expected_source_doc"] for g in golden}
    print(f"wrote {len(golden)} questions covering {len(docs)} docs -> {out}")


if __name__ == "__main__":
    main()
