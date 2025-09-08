#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrahiert alle Header-Informationen, die in split_Taeuferquellen_tei.py erzeugt werden, aus einer unsegmentierten TEI/XML-Datei und schreibt sie in eine Excel-Datei.

- Erwartet eine große TEI/XML-Datei mit mehreren <div type="document">-Blöcken
- Extrahiert: Index, Titel (<head>), Vorlage (<idno>), Datum (<origDate>), alle <respStmt> (Transkript/Tagging), ggf. weitere Felder aus dem Header
- Schreibt die Daten in eine Excel-Datei (XLSX)

Aufruf:
    python extract_full_tei_headers_to_excel.py input.xml output.xlsx
"""

from pathlib import Path
import argparse
from lxml import etree
import openpyxl

TEI_NS = "http://www.tei-c.org/ns/1.0"

FIELDS = [
    ("index", "Nr."),
    ("head", "Titel/Head"),
    ("idno", "Vorlage/Idno"),
    ("origDate", "Datum (origDate)"),
    ("transcript", "Transkript (Personen)"),
    ("tagging", "Tagging (Personen)"),
    ("publisher", "Publisher"),
    ("series_idno", "Serien-ID"),
    ("source_title", "Serientitel"),
]

def extract_header_info_from_div(div, nsmap, tei_prefix):
    def xp(tag):
        if tei_prefix:
            return f'.//{tei_prefix}:{tag}'
        else:
            return f'.//{tag}'
    # head
    head_el = div.xpath(xp("head"), namespaces=nsmap)
    head = head_el[0].text.strip() if head_el and head_el[0].text else ""
    # original/idno (source reference)
    idno = ""
    for v in div.xpath(xp("div"), namespaces=nsmap):
        if v.get("type") == "original":
            idno_el = v.xpath(xp("idno"), namespaces=nsmap)
            if idno_el and idno_el[0].text:
                idno = idno_el[0].text.strip()
            else:
                idno = v.text.strip() if v.text else ""
            break
    # origDate
    origDate = ""
    for s in div.xpath(xp("div"), namespaces=nsmap):
        if s.get("type") == "source":
            date_el = s.xpath(xp("origDate"), namespaces=nsmap)
            if date_el:
                origDate = date_el[0].get("when", "")
            else:
                origDate = s.get("date", "")
            break
    # respStmt (Transkript/Tagging)
    transcript = ""
    tagging = ""
    # Suche nach respStmt in der Hierarchie (wie im Header von split_Taeuferquellen_tei.py)
    respstmts = div.xpath(xp("respStmt"), namespaces=nsmap)
    for r in respstmts:
        resp = r.find(xp("resp"), namespaces=nsmap)
        pers = r.find(xp("persName"), namespaces=nsmap)
        if resp is not None and resp.get("key") == "transcript":
            transcript = pers.text.strip() if pers is not None and pers.text else ""
        if resp is not None and resp.get("key") == "tagging":
            tagging = pers.text.strip() if pers is not None and pers.text else ""
    # publisher
    publisher = ""
    pub_el = div.xpath(xp("publisher"), namespaces=nsmap)
    if pub_el and pub_el[0].text:
        publisher = pub_el[0].text.strip()
    # seriesStmt/idno
    series_idno = ""
    ser_id_el = div.xpath(xp("idno"), namespaces=nsmap)
    if ser_id_el and ser_id_el[0].text:
        series_idno = ser_id_el[0].text.strip()
    # seriesStmt/title
    source_title = ""
    ser_title_el = div.xpath(xp("title"), namespaces=nsmap)
    if ser_title_el and ser_title_el[0].text:
        source_title = ser_title_el[0].text.strip()
    return {
        "head": head,
        "idno": idno,
        "origDate": origDate,
        "transcript": transcript,
        "tagging": tagging,
        "publisher": publisher,
        "series_idno": series_idno,
        "source_title": source_title,
    }

def main():
    ap = argparse.ArgumentParser(description="Extrahiert alle Header-Infos aus unsegmentierter TEI/XML in Excel.")
    ap.add_argument("input_xml", type=Path, help="Pfad zur Eingabe-TEI/XML-Datei")
    ap.add_argument("output_xlsx", type=Path, help="Pfad zur Ausgabedatei (xlsx)")
    args = ap.parse_args()

    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(args.input_xml), parser)
    root = tree.getroot()
    nsmap = root.nsmap.copy() if hasattr(root, 'nsmap') else {}
    tei_prefix = None
    for k, v in nsmap.items():
        if v == TEI_NS:
            tei_prefix = k or 'tei'
            break
    if not tei_prefix:
        nsmap = {}
        tei_prefix = None
    def xp(tag):
        if tei_prefix:
            return f'.//{tei_prefix}:{tag}'
        else:
            return f'.//{tag}'
    # Alle <div type="document">
    doc_divs = [d for d in root.xpath(xp("div"), namespaces=nsmap) if d.get("type") == "document"]
    if not doc_divs:
        print('Keine <div type="document">-Elemente gefunden.')
        return
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TEI Header Infos"
    ws.append([label for _, label in FIELDS])
    for idx, div in enumerate(doc_divs, start=1):
        info = extract_header_info_from_div(div, nsmap, tei_prefix)
        row = [idx] + [info[field] for field, _ in FIELDS if field != "index"]
        ws.append(row)
    wb.save(str(args.output_xlsx))
    print(f"Excel-Datei geschrieben: {args.output_xlsx}")

if __name__ == "__main__":
    main()
