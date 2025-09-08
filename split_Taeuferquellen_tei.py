#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Segmentiert eine lange XML mit <div type="document"> in viele TEI-Dateien.

- <p> aus dem Ausgangs-<div type="document"> werden innerhalb von <body><div> übernommen.
- <div type="source" date="1542 Oktober 25"> -> <origDate when="1542-10-25"/>
- <head> wird in den Header (<msDesc><head>) übernommen.
- <div type="vorlage"> -> <msIdentifier><idno> (Entfernt "Vorlage:" sowie das Komma nach "StAZH"; normalisiert zu 'StAZH').
- Falls es <note type="editorial"> gibt, werden deren Inhalte nach <body> in <back> geschrieben, je Note in ein eigenes <p>.
- Erstellt für jede Segment-Datei den angegebenen TEI-Header und die gewünschte XML-PI.

Aufruf:
    python split_tei.py /pfad/zu/eingabe.xml /pfad/zum/ausgabeordner --prefix QZH
"""

from pathlib import Path
import re
import argparse
from copy import deepcopy
from lxml import etree

TEI_NS = "http://www.tei-c.org/ns/1.0"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

# Deutsche Monatsnamen (inkl. Varianten)
MONTHS = {
    "januar": "01", "jan": "01",
    "februar": "02", "feb": "02",
    "märz": "03", "maerz": "03", "mrz": "03", "marz": "03",
    "april": "04", "apr": "04",
    "mai": "05",
    "juni": "06", "jun": "06",
    "juli": "07", "jul": "07",
    "august": "08", "aug": "08",
    "september": "09", "sept": "09", "sep": "09",
    "oktober": "10", "october": "10", "okt": "10", "oct": "10",
    "november": "11", "nov": "11",
    "dezember": "12", "december": "12", "dez": "12", "dec": "12",
}

def to_iso_date(date_str: str) -> str | None:
    """
    Erwartet z.B. '1542 Oktober 25' (Reihenfolge tolerant).
    Liefert '1542-10-25' oder None.
    """
    if not date_str:
        return None
    s_norm = re.sub(r"\s+", " ", date_str.strip())

    # Bereits ISO?
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s_norm):
        return s_norm

    tokens = re.split(r"[.\s,;/\-]+", s_norm)
    toks = [t for t in tokens if t]
    if len(toks) < 3:
        return None

    def monthnum(tok: str) -> str | None:
        return MONTHS.get(tok.lower())

    # YYYY MON DD
    if toks[0].isdigit() and len(toks[0]) == 4 and monthnum(toks[1]) and toks[2].isdigit():
        y, m, d = toks[0], monthnum(toks[1]), toks[2].zfill(2)
        return f"{y}-{m}-{d}"

    # DD MON YYYY
    if toks[0].isdigit() and monthnum(toks[1]) and toks[2].isdigit() and len(toks[2]) == 4:
        d, m, y = toks[0].zfill(2), monthnum(toks[1]), toks[2]
        return f"{y}-{m}-{d}"

    # YYYY MON (ohne Tag) -> 01
    if toks[0].isdigit() and len(toks[0]) == 4 and monthnum(toks[1]):
        y, m = toks[0], monthnum(toks[1])
        return f"{y}-{m}-01"

    return None

def clean_vorlage(text: str) -> str:
    """
    Entfernt führendes 'Vorlage:' (case-insensitive) und
    normalisiert 'StAZH' (Komma nach StAZH löschen, Schreibweise vereinheitlichen).
    """
    if not text:
        return ""
    t = text.strip()
    # "Vorlage:" am Anfang entfernen (falls vorhanden)
    t = re.sub(r"^\s*vorlage\s*:\s*", "", t, flags=re.IGNORECASE)
    # Komma nach StAZH entfernen (auch mit variierenden Whitespaces) und Schreibweise vereinheitlichen
    t = re.sub(r"\bstazh\s*,\s*", "StAZH ", t, flags=re.IGNORECASE)
    # Falls ohne Komma, aber falsche Groß-/Kleinschreibung: angleichen
    t = re.sub(r"\bstazh\b", "StAZH", t, flags=re.IGNORECASE)
    return t.strip()

def tei_el(tag, **attrib):
    return etree.Element(f"{{{TEI_NS}}}{tag}", attrib)

def tei_sub(parent, tag, text=None, **attrib):
    el = etree.SubElement(parent, f"{{{TEI_NS}}}{tag}", attrib)
    if text is not None:
        el.text = text
    return el

def build_header(head_text: str | None, idno_text: str | None, iso_date: str | None) -> etree._Element:
    teiHeader = tei_el("teiHeader")

    fileDesc = tei_sub(teiHeader, "fileDesc")
    titleStmt = tei_sub(fileDesc, "titleStmt")
    tei_sub(titleStmt, "title", "Quellen zur Zürcher Geschichte")

    respStmt1 = tei_sub(titleStmt, "respStmt")
    tei_sub(respStmt1, "persName", "Christian Scheidegger. Unter Mitarbeit von Daniela Dettwiler")
    tei_sub(respStmt1, "resp", None, **{"key": "transcript"})

    respStmt2 = tei_sub(titleStmt, "respStmt")
    tei_sub(respStmt2, "persName", "Christian Scheidegger. Unter Mitarbeit von Daniela Dettwiler")
    tei_sub(respStmt2, "resp", None, **{"key": "tagging"})

    publicationStmt = tei_sub(fileDesc, "publicationStmt")
    tei_sub(publicationStmt, "publisher", "Staatsarchiv des Kantons Zürich")
    tei_sub(publicationStmt, "date", None, **{"type": "electronic", "when": "2021-05-01"})

    seriesStmt = tei_sub(fileDesc, "seriesStmt")
    tei_sub(seriesStmt, "title", "Quellen zur Zürcher Geschichte")
    rs = tei_sub(seriesStmt, "respStmt")
    tei_sub(rs, "persName", "Christian Scheidegger, Tobias Jammerthal")
    tei_sub(rs, "resp", "Herausgeberschaft")
    tei_sub(seriesStmt, "idno", "QZH_150")

    sourceDesc = tei_sub(fileDesc, "sourceDesc")
    msDesc = tei_sub(sourceDesc, "msDesc")
    msIdentifier = tei_sub(msDesc, "msIdentifier")
    tei_sub(msIdentifier, "idno", idno_text or "")

    # <head> aus Dokument
    tei_sub(msDesc, "head", head_text or "")

    msContents = tei_sub(msDesc, "msContents")
    msItem = tei_sub(msContents, "msItem")
    tei_sub(msItem, "textLang", "Deutsch")
    tei_sub(msItem, "filiation", "Aufzeichnung, Heft (9 Blätter)", **{"type": "current"})
    filiation_orig = tei_sub(msItem, "filiation", None, **{"type": "original"})
    if iso_date:
        tei_sub(filiation_orig, "origDate", None, **{"when": iso_date})

    physDesc = tei_sub(msDesc, "physDesc")
    objectDesc = tei_sub(physDesc, "objectDesc")
    supportDesc = tei_sub(objectDesc, "supportDesc")
    support = tei_sub(supportDesc, "support")
    tei_sub(support, "material", "Papier")
    tei_sub(supportDesc, "extent", "")

    history = tei_sub(msDesc, "history")
    tei_sub(history, "origin", "")

    encodingDesc = tei_sub(teiHeader, "encodingDesc")
    editorialDecl = tei_sub(encodingDesc, "editorialDecl")
    p = tei_sub(editorialDecl, "p")
    tei_sub(p, "ref", None, **{"target": "https://www.ssrq-sds-fds.ch/wiki/Transkriptionsrichtlinien"})

    tei_sub(teiHeader, "profileDesc")
    profileDesc = tei_sub(teiHeader, "profileDesc")
    tei_sub(profileDesc, "textClass", None, **{"default": "false"})

    return teiHeader

def build_tei_tree(head_text, idno_text, iso_date, p_nodes, editorial_notes):
    # Root mit Namespaces
    root = etree.Element("{%s}TEI" % TEI_NS, nsmap={None: TEI_NS, "xsi": XSI_NS})
    # Header
    teiHeader = build_header(head_text, idno_text, iso_date)
    root.append(teiHeader)

    # Text / Body
    text = tei_sub(root, "text")
    body = tei_sub(text, "body")
    div = tei_sub(body, "div")

    for p in p_nodes:
        div.append(deepcopy(p))

    # <back> für editoriale Notizen (falls vorhanden)
    if editorial_notes:
        back = tei_sub(text, "back")
        for note in editorial_notes:
            p = tei_sub(back, "p")
            p.text = (note.text or None)
            for child in note:
                p.append(deepcopy(child))

    return root

def extract_first_text(el) -> str | None:
    if el is None:
        return None
    return "".join(el.itertext()).strip()

def process(input_xml: Path, outdir: Path, prefix: str = "doc"):
    outdir.mkdir(parents=True, exist_ok=True)

    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(input_xml), parser)
    root = tree.getroot()

    # Namespace-Erkennung
    nsmap = root.nsmap.copy() if hasattr(root, 'nsmap') else {}
    tei_prefix = None
    for k, v in nsmap.items():
        if v == TEI_NS:
            tei_prefix = k or 'tei'
            break
    has_tei_ns = tei_prefix is not None
    if not has_tei_ns:
        nsmap = {}  # keine Namespaces
        tei_prefix = None

    def xp(tag):
        if has_tei_ns:
            return f'.//{tei_prefix}:{tag}'
        else:
            return f'.//{tag}'

    # Alle <div type="document">
    doc_divs = []
    for d in root.xpath(xp("div"), namespaces=nsmap):
        if d.get("type") == "document":
            doc_divs.append(d)

    if not doc_divs:
        print('Keine <div type="document">-Elemente gefunden.')
        return

    for idx, d in enumerate(doc_divs, start=1):
        # p-Knoten innerhalb des Dokument-div (rekursiv)
        p_nodes = []
        for p in d.xpath(xp("p"), namespaces=nsmap):
            if d in p.iterancestors():
                p_nodes.append(p)

        # head (erster Treffer)
        head_el = None
        res = d.xpath(xp("head"), namespaces=nsmap)
        if res:
            head_el = res[0]
        head_text = extract_first_text(head_el)

        # original (source reference)
        original_el = None
        for v in d.xpath(xp("div"), namespaces=nsmap):
            if v.get("type") == "original":
                original_el = v
                break
        idno_text = clean_vorlage(extract_first_text(original_el) or "")

        # source date
        iso_when = None
        for s_el in d.xpath(xp("div"), namespaces=nsmap):
            if s_el.get("type") == "source":
                date_attr = s_el.get("date") or ""
                iso_when = to_iso_date(date_attr)
                if iso_when:
                    break

        # editoriale Notizen sammeln
        editorial_notes = []
        for n in d.xpath(xp("note"), namespaces=nsmap):
            if n.get("type") == "editorial":
                editorial_notes.append(n)

        # TEI-Baum bauen
        tei_root = build_tei_tree(head_text, idno_text, iso_when, p_nodes, editorial_notes)

        # Stylesheet-PI vor Root setzen
        pi = etree.ProcessingInstruction(
            "xml-stylesheet", "type='text/xsl' href='../../Ressourcen/Stylesheet.xsl'"
        )
        tei_tree = etree.ElementTree(tei_root)
        tei_root.addprevious(pi)

        # Dateiname: optional mit <head>

        safe_head = (head_text or "").strip()
        safe_head = re.sub(r"\s+", "_", safe_head)
        safe_head = re.sub(r"[^\w\-_.]", "", safe_head, flags=re.UNICODE)
        # Begrenze safe_head auf 80 Zeichen, damit der gesamte Dateiname < 100 Zeichen bleibt
        max_head_len = 80
        if len(safe_head) > max_head_len:
            safe_head = safe_head[:max_head_len].rstrip('_')
        suffix = f"_{safe_head}" if safe_head else ""
        filename = f"{prefix}_{idx:03d}{suffix}.xml"
        # Falls der Dateiname immer noch zu lang ist, kürzen
        max_filename_len = 100
        if len(filename) > max_filename_len:
            filename = filename[:max_filename_len-4] + ".xml"
        out_path = outdir / filename

        # Schreiben
        tei_tree.write(
            str(out_path),
            encoding="UTF-8",
            xml_declaration=True,
            pretty_print=True,
        )
        print(f"Geschrieben: {out_path}")

def main():
    ap = argparse.ArgumentParser(description="Segmentiert TEI/XML nach <div type='document'> in einzelne Dateien.")
    ap.add_argument("input", type=Path, help="Pfad zur Eingabe-XML")
    ap.add_argument("outdir", type=Path, help="Ausgabe-Ordner")
    ap.add_argument("--prefix", default="doc", help="Dateinamen-Präfix (Default: doc)")
    args = ap.parse_args()

    process(args.input, args.outdir, args.prefix)

if __name__ == "__main__":
    main()
