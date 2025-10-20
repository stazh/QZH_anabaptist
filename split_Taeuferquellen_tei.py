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
    t = re.sub(r"^\s*vorlage\s*:\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bstazh\s*,\s*", "StAZH ", t, flags=re.IGNORECASE)
    t = re.sub(r"\bstazh\b", "StAZH", t, flags=re.IGNORECASE)
    return t.strip()

def tei_el(tag, **attrib):
    return etree.Element(f"{{{TEI_NS}}}{tag}", attrib)

def tei_sub(parent, tag, text=None, **attrib):
    el = etree.SubElement(parent, f"{{{TEI_NS}}}{tag}", attrib)
    if text is not None:
        el.text = text
    return el

def build_header(head_text: str | None, idno_text: str | None, iso_date: str | None, qgts_nr: str | None = None) -> etree._Element:
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
    tei_sub(seriesStmt, "idno", idno_text or "QZH_150")

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
    # optionales <additional> direkt unter <history>
    if qgts_nr:
        additional = tei_sub(history, "additional")
        listBibl = tei_sub(additional, "listBibl")
        tei_sub(listBibl, "head", "Edition")
        bibl_outer = tei_sub(listBibl, "bibl")
        bibl_inner = tei_sub(bibl_outer, "bibl")
        ref_el = tei_sub(bibl_inner, "ref", "QGTS", **{"target": "https://qzh.sources-online.org/exist/apps/qzh/literaturverzeichnis.html"})
        if ref_el is not None:
            ref_el.tail = f", Bd. 5, Nr. {qgts_nr}"

    encodingDesc = tei_sub(teiHeader, "encodingDesc")
    editorialDecl = tei_sub(encodingDesc, "editorialDecl")
    p = tei_sub(editorialDecl, "p")
    tei_sub(p, "ref", None, **{"target": "https://www.ssrq-sds-fds.ch/wiki/Transkriptionsrichtlinien"})

    # Nur EIN profileDesc
    profileDesc = tei_sub(teiHeader, "profileDesc")
    tei_sub(profileDesc, "textClass", None, **{"default": "false"})

    return teiHeader

def extract_first_text(el) -> str | None:
    if el is None:
        return None
    return "".join(el.itertext()).strip()

def fix_inline_persnames(p_el: etree._Element):
    """
    Sucht ein zweiteiliges Namensmuster unmittelbar vor einem leeren <persName/> und
    überträgt es als Text in <persName>. Mutiert p_el in-place.
    """
    for pers in p_el.xpath('.//*[local-name()="persName"]'):
        if (pers.text and pers.text.strip()):
            continue

        parent = pers.getparent()
        if parent is None:
            continue

        children = list(parent)
        try:
            pos = children.index(pers)
        except ValueError:
            pos = -1

        if pos > 0:
            prev = children[pos - 1]
            text_segment = prev.tail or ''
            target_container = ('tail', prev)
        else:
            text_segment = parent.text or ''
            target_container = ('text', parent)

        tokens = re.findall(r"\S+", text_segment)
        if len(tokens) >= 2:
            name = tokens[-2] + ' ' + tokens[-1]
            remaining_tokens = tokens[:-2]
            remaining = ' '.join(remaining_tokens)

            if all(any(ch.isalpha() for ch in t) for t in (tokens[-2], tokens[-1])):
                pers.text = name
                if target_container[0] == 'tail':
                    prev.tail = (remaining if remaining else None)
                else:
                    parent.text = (remaining if remaining else None)
                if pers.tail:
                    pers.tail = pers.tail.lstrip()

def fix_inline_placenames(p_el: etree._Element) -> None:
    """
    Wandelt <placeName ref="X"/> direkt nach einem Wort in <placeName ref="X">Wort</placeName> um.
    Nimmt an, dass das Wort unmittelbar davor steht (Parent.text oder previous.tail).
    """
    for pn in p_el.xpath('.//*[local-name()="placeName" and not(normalize-space())]'):
        prev = pn.getprevious()
        parent = pn.getparent()
        token = None
        if prev is None:
            if parent is not None and parent.text:
                parts = parent.text.rstrip().rsplit(None, 1)
                if parts:
                    token = parts[-1]
                    parent.text = parent.text[: -len(token)].rstrip() if len(parts) > 1 else ''
        else:
            tail = (prev.tail or '').rstrip()
            if tail:
                parts = tail.rsplit(None, 1)
                if parts:
                    token = parts[-1]
                    prev.tail = prev.tail[: -len(token)].rstrip() if len(parts) > 1 else ''
        if token:
            pn.text = token
            pn.tail = (pn.tail or '').lstrip()

def build_tei_tree(head_text, idno_text, iso_date, p_nodes, editorial_notes, qgts_nr: str | None = None):
    # Root mit Namespaces
    root = etree.Element("{%s}TEI" % TEI_NS, nsmap={None: TEI_NS, "xsi": XSI_NS})
    # Header
    teiHeader = build_header(head_text, idno_text, iso_date, qgts_nr)
    root.append(teiHeader)

    # Text / Body
    text = tei_sub(root, "text")
    body = tei_sub(text, "body")
    div = tei_sub(body, "div")

    for p in p_nodes:
        p_copy = deepcopy(p)
        try:
            fix_inline_persnames(p_copy)
            fix_inline_placenames(p_copy)
        except Exception:
            pass
        div.append(p_copy)

    # <back> für editoriale Notizen (falls vorhanden)
    if editorial_notes:
        back = tei_sub(text, "back")
        for note in editorial_notes:
            p = tei_sub(back, "p")
            p.text = (note.text or None)
            for child in note:
                p.append(deepcopy(child))

    return root  # (kein doppeltes return mehr)

def process(input_xml: Path, outdir: Path, prefix: str = "doc"):
    outdir.mkdir(parents=True, exist_ok=True)

    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(input_xml), parser)

    # Alle Dokument-DIVs (namespace-agnostisch)
    divs = tree.xpath('//*[local-name()="div" and @type="document"]')

    for idx, d in enumerate(divs, start=150):
        # head
        head_el = d.xpath('.//*[local-name()="head"]')
        head_text = extract_first_text(head_el[0]) if head_el else ""

        # idno aus vorlage/oderiginal
        vorlage_el = d.xpath('.//*[local-name()="div" and @type="vorlage"]')
        original_el = d.xpath('.//*[local-name()="div" and @type="original"]')
        idno_text = ""
        if vorlage_el:
            idno_text = clean_vorlage(extract_first_text(vorlage_el[0]) or "")
        elif original_el:
            idno_text = clean_vorlage(extract_first_text(original_el[0]) or "")

        # p-Knoten
        p_nodes = d.xpath('.//*[local-name()="p"]')

        # source date und qgts-nr
        iso_when = None
        qgts_nr = None
        s_el = d.xpath('.//*[local-name()="div" and @type="source"]')
        if s_el:
            date_attr = s_el[0].get('date') or ''
            iso_when = to_iso_date(date_attr)
            qgts_nr = s_el[0].get('n')

        # editoriale Notizen nur wenn innerhalb von <head>
        editorial_notes = []
        for n in d.xpath('.//*[local-name()="note" and @type="editorial"]'):
            if any((anc.tag.endswith("head")) for anc in n.iterancestors()):
                editorial_notes.append(n)

        # TEI bauen
        series_idno = f"{prefix}_{idx}"
        tei_root = build_tei_tree(head_text, series_idno, iso_when, p_nodes, editorial_notes, qgts_nr)

        # PI voranstellen
        pi = etree.ProcessingInstruction(
            "xml-stylesheet",
            "type='text/xsl' href='../../Ressourcen/Stylesheet.xsl'"
        )

        tei_root.addprevious(pi)

        # Schreiben IN der Schleife, prefix verwenden
        filename = f"{prefix}_{idx}.xml"
        out_path = outdir / filename
        print(f"DEBUG: writing to {out_path}")
        tei_tree = etree.ElementTree(tei_root)
        tei_tree.write(str(out_path), encoding="UTF-8", xml_declaration=True, pretty_print=True)
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
