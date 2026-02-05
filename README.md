# QGTS 2 QZH — TEI Utilities

This repository contains two small Python command-line tools to work with **TEI/XML** data from the *Quellen zur Geschichte der Taeufer in der Schweiz* and *Quellen zur Zürcher Geschichte* context:

1. **Split a large TEI/XML file into many TEI files** (one per `<div type="document">`).
2. **Extract TEI header metadata into an Excel spreadsheet**.

The scripts are intended to be run locally from the command line.

---

## Contents

* `Split_Anabaptist_tei.py` — split one large TEI/XML into many TEI documents 
* `extract_full_tei_headers_to_excel.py` — export TEI header information to `.xlsx` 

---

## Requirements

* Python 3.8+ (recommended)
* Dependencies:

  * `lxml`
  * `openpyxl` (only for the Excel export script)

Install dependencies:

```bash
pip install lxml openpyxl
```

---

## 1) Split a large TEI/XML into separate TEI files

**Script:** `Split_Anabaptist_tei.py` 

### What it does

* Reads an input XML/TEI file containing many documents stored as:

  * `<div type="document"> ... </div>`
* Writes **one TEI file per document** into an output folder.
* Builds a fresh TEI structure per output file:

  * Adds a generated `<teiHeader>` (title, publication statement, series info, msDesc, etc.)
  * Copies document content into `<text><body><div>...</div></body></text>`
  * Copies editorial notes from the document head into `<text><back>...</back></text>` (mixed content preserved)
* Tries to normalize / enrich some content:

  * Includes `<pb/>` correctly even if it is a sibling of `<p>` (prevents duplicates)
  * Fixes empty inline `<persName/>` by moving the last two preceding words into the element (heuristic)
  * Fixes empty `<placeName/>` by moving the last preceding token into the element (heuristic)
* Adds an `xml-stylesheet` processing instruction to the output TEI (stylesheet path is hardcoded in the script).

### Output naming / indexing

* Output filenames use `--prefix` plus an index:

  * `PREFIX_115.xml`, `PREFIX_116.xml`, ...
* **Important:** the script currently starts numbering at **115** (`enumerate(..., start=115)`), which may be intentional for alignment with an external numbering scheme. If you need numbering to start at 1, change that line in the script. 

### Usage

```bash
python Split_Anabaptist_tei.py /path/to/input.xml /path/to/output_dir --prefix QZH
```

**Arguments**

* `input` — path to the input XML/TEI file
* `outdir` — folder for generated TEI files (created if missing)
* `--prefix` — filename prefix (default: `doc`)

### Example

```bash
python Split_Anabaptist_tei.py data/QZH_all.xml out/tei --prefix QZH
# -> out/tei/QZH_115.xml, out/tei/QZH_116.xml, ...
```

---

## 2) Extract TEI header information to Excel

**Script:** `extract_full_tei_headers_to_excel.py` 

### What it does

* Parses a TEI/XML file that contains multiple `<div type="document">` blocks.
* Extracts key header-ish metadata per document and writes one row per document into an Excel file (`.xlsx`).

### Fields written to Excel

The spreadsheet columns are:

* **Nr.** — running index (1..N)
* **Titel/Head** — first `<head>` text found in the document
* **Vorlage/Idno (Überlieferungsträger)** — combined string from any of:

  * `<div type="original">`, `<div type="vorlage">`, `<div type="Abschrift">`, `<div type="Edition">`
  * joined with `; `
* **Datum (origDate)** — usually taken from `<origDate when="...">`, otherwise from `@date` on `<div type="source">`
* **Überlieferung** — any text inside parentheses found in the carrier fields above (also joined with `; `)
* **Transkript (Personen)** — names from `<respStmt>` where `<resp key="transcript">`
* **Tagging (Personen)** — names from `<respStmt>` where `<resp key="tagging">`
* **Publisher** — `<publisher>`
* **Serien-ID** — first `<idno>` encountered (note: this is a simple “first match” strategy)
* **Serientitel** — first `<title>` encountered (also “first match” strategy)

The script supports TEI namespace parsing and falls back to non-namespaced queries if needed. 

### Usage

```bash
python extract_full_tei_headers_to_excel.py /path/to/input.xml /path/to/output.xlsx
```

### Example

```bash
python extract_full_tei_headers_to_excel.py out/tei/QZH_all.xml out/QZH_headers.xlsx
```

### Output formatting

* Header row is bold
* Column **C** is widened and wrapped (long carrier strings)
* Column **E** is widened and wrapped (Überlieferung)

---

## Notes / Tips

* Both scripts expect **well-formed XML**. The Excel script uses `recover=True` to be tolerant of some parsing issues, but clean TEI is strongly recommended. 
* If your TEI uses different structures for source/date or carriers, you may need to adapt the XPath expressions in the scripts.
* The stylesheet path added by the splitter is currently:

  * `../../Ressourcen/Stylesheet.xsl` 

---

## License

No license file is included here. If you plan to publish or reuse this code broadly, consider adding a `LICENSE` file to the repository.
