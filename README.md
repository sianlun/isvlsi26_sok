# SoK on TinyML Trade-offs in Healthcare IoMT — Reproducibility Package

This folder contains the code, bibliographic metadata, and pre-built
extraction workbooks supporting the paper *"A Systematization of Knowledge
(SoK) on TinyML Trade-offs in Healthcare IoMT"*. It lets a reviewer
reproduce the 77-paper corpus, the two independent extraction passes, and
the three-dimensional decision matrix reported in the paper.

## What is included

| File | Purpose |
|---|---|
| `corpus_final.json`, `CORPUS.md` | 77-paper manifest (title, DOI, filename, year) |
| `extract.py`, `_extracted.json` | Round 1 pipeline (Poppler `pdftotext`, 6 pages, keyword-first tier) |
| `extract_alt.py`, `_extracted_alt.json` | Round 2 pipeline (`pypdf`, 12 pages, MCU-family-first tier) |
| `build_xlsx.py`, `SoK_extraction_template.xlsx` | Round 1 workbook + precomputed Matrix |
| `build_alt_and_verify.py`, `SoK_extraction_Alt.xlsx` | Round 2 workbook + Verification, Disagreements, Matrix_Compare sheets |

## What is NOT included

The 77 source PDFs are copyrighted by their respective publishers and are
excluded via `.gitignore`. Derived plain-text extracts (`_txt/`,
`_txt_alt/`) are likewise excluded. Obtain the PDFs yourself from the DOIs
in `corpus_final.json` / `download_manual.json` using open-access links or
institutional subscriptions.

## Requirements

- Python 3.10+
- Poppler `pdftotext` on PATH (tested with 22.02.0)
- `pip install -r requirements.txt` (`pypdf`, `openpyxl`)

## Reproduction steps

```bash
# 1. Fetch open-access PDFs listed in download_oa.json
bash download_oa.sh

# 2. Fetch the other PDFs via proper channels

# 3. Generate plain-text extracts for Round 1 (Poppler, first 6 pages)
mkdir -p _txt
for f in *.pdf; do
  pdftotext -l 6 "$f" "_txt/${f%.pdf}.txt"
done

# 4. Generate plain-text extracts for Round 2 (pypdf, first 12 pages)
mkdir -p _txt_alt
python3 -c "
import os, pypdf
for f in sorted(os.listdir('.')):
    if not f.endswith('.pdf'): continue
    r = pypdf.PdfReader(f)
    text = '\n'.join(p.extract_text() or '' for p in r.pages[:12])
    open(f'_txt_alt/{f[:-4]}.txt', 'w').write(text)
"

# 5. Round 1 extraction + workbook
python3 extract.py           # -> _extracted.json
python3 build_xlsx.py        # -> SoK_extraction_template.xlsx

# 6. Round 2 extraction + cross-verification workbook
python3 extract_alt.py       # -> _extracted_alt.json
python3 build_alt_and_verify.py   # -> SoK_extraction_Alt.xlsx
```

## Pipeline differences at a glance

| | Round 1 (`extract.py`) | Round 2 (`extract_alt.py`) |
|---|---|---|
| Text engine | Poppler `pdftotext` | `pypdf.PdfReader` |
| Page window | First 6 pages | First 12 pages |
| Text window used | 12 000 chars | 20 000 chars |
| Tier policy | Keyword-first (implant/bedside/... → tier; else MCU fallback) | MCU-family-first (MCU → tier; implant/bedside override) |
| Technique vocabulary | 7 entries, presence flags | 4 entries, match-count weighted |
| Accuracy regex | Matches numbers with or without `%` | Requires explicit `%` |
| Output fields | 16 (15 extracted + blank `Notes (manual)`) | 15 |

Both pipelines emit the same primary keys (including `Clinical Domain`).
Agreement per field and the 14 matrix-level disagreements are reported in
the `Verification` and `Matrix_Compare` sheets of
`SoK_extraction_Alt.xlsx`.

## Consensus matrix

For each cell *(technique, device tier, clinical domain)*, the consensus
count used in the paper is the element-wise minimum of the two pipelines'
counts. Cells with consensus ≥ 2 are the cells reported as empirically
supported in the paper's decision matrix.

## AI tools usage

The code and also the generation of the github repository contents have been checked and reviewed using Claude AI/Opus 4.6. Research team has also manually verified as thoroughly as possible to ensure the work can be validated/reproduced. 

## License

Code: MIT (see `LICENSE`). Source PDFs: respective publishers; not
included. Extraction tables and decision-matrix counts derived from the
corpus are released alongside the paper under the paper's own terms.

## Citation

Please cite the accompanying paper. A BibTeX entry will be added here
after the paper is accepted for publication. 
