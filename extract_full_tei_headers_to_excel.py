#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrahiert Header-Infos aus TEI/XML in Excel.

- Berücksichtigt <div type="original">, <div type="vorlage">,
  <div type="Abschrift">, <div type="Edition"> für Spalte C.
  Diese werden zu einem String mit Strichpunkten verbunden.
- Inhalt in runden Klammern aus diesen divs wird in eigene Spalte
  "Überlieferung" (Spalte E) geschrieben.
"""

from pathlib import Path
import argparse
import re
from lxml import etree
import openpyxl
from openpyxl.styles import Font, Alignment

# Fester Namespace für TEI
NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

FIELDS = [
    ("index", "Nr."),                                   # A
    ("head", "Titel/Head"),                            # B
    ("idno", "Vorlage/Idno (Überlieferungsträger)"),   # C
    ("origDate", "Datum (origDate)"),                  # D
    ("ueberlieferung", "Überlieferung"),               # E
    ("transcript", "Transkript (Personen)"),           # F
    ("tagging", "Tagging (Personen)"),                 # G
    ("publisher", "Publisher"),                        # H
    ("series_idno", "Serien-ID"),                      # I
    ("source_title", "Serientitel"),                   # J
]

def safe_get_text(element_list):
    """Hilfsfunktion: Gibt Text des ersten Elements zurück oder leeren String."""
    if element_list and element_list[0].text:
        return element_list[0].text.strip()
    return ""

def extract_header_info_from_div(div):
    """Extrahiert Metadaten aus einem <div type='document'>-Block."""

    # Helper: erst mit Namespace, dann ohne Namespace probieren
    def xp(path_with_tei, path_plain):
        res = div.xpath(path_with_tei, namespaces=NS)
        if res:
            return res
        return div.xpath(path_plain)

    # 1. Head (Titel)
    head = safe_get_text(xp(".//tei:head", ".//head"))

    # 2. Überlieferungsträger (Idno / Vorlage / Original / Abschrift / Edition)
    # Wir sammeln ALLE relevanten <div type="..."> und hängen sie mit ";" zusammen.
    idno = ""
    ueberlieferung = ""

    carrier_divs = xp(
        ".//tei:div[@type='original' or @type='vorlage' or @type='Abschrift' or @type='Edition']",
        ".//div[@type='original' or @type='vorlage' or @type='Abschrift' or @type='Edition']"
    )

    base_parts = []
    ueberlieferung_parts = []

    for s_div in carrier_divs:
        # 1. Versuch: <idno> innerhalb dieses div (mit und ohne Namespace)
        idno_el = s_div.xpath(".//tei:idno", namespaces=NS) or s_div.xpath(".//idno")
        if idno_el:
            raw_text = safe_get_text(idno_el)
        else:
            # Falls kein <idno>, gesamten Text inkl. Kinder zusammensetzen
            raw_text = "".join(s_div.itertext()).strip()

        if not raw_text:
            continue

        # Alle Klammerinhalte einsammeln
        parens = re.findall(r"\(([^()]*)\)", raw_text)
        if parens:
            ueberlieferung_parts.extend([p.strip() for p in parens if p.strip()])
            no_paren = re.sub(r"\s*\([^()]*\)", "", raw_text)
        else:
            no_paren = raw_text

        # Aufräumen: Whitespace und überstehende Trennzeichen
        no_paren = no_paren.strip().rstrip(",;")
        if no_paren:
            base_parts.append(no_paren)

    if base_parts:
        idno = "; ".join(base_parts)
    if ueberlieferung_parts:
        ueberlieferung = "; ".join(ueberlieferung_parts)

    # 3. Datum (origDate)
    origDate = ""
    date_divs = xp(".//tei:div[@type='source']", ".//div[@type='source']")
    if date_divs:
        src = date_divs[0]
        date_el = src.xpath(".//tei:origDate", namespaces=NS) or src.xpath(".//origDate")
        if date_el:
            origDate = date_el[0].get("when", "")
            if not origDate:
                origDate = date_el[0].text.strip() if date_el[0].text else ""
        else:
            origDate = src.get("date", "")

    # 4. RespStmt (Transkript/Tagging)
    transcribers = []
    taggers = []

    respstmts = xp(".//tei:respStmt", ".//respStmt")
    for r in respstmts:
        resp = r.find("tei:resp", namespaces=NS) or r.find("resp")
        pers = r.find("tei:persName", namespaces=NS) or r.find("persName")

        if resp is not None and pers is not None and pers.text:
            role = resp.get("key")
            name = pers.text.strip()

            if role == "transcript":
                transcribers.append(name)
            elif role == "tagging":
                taggers.append(name)

    # 5. Publisher
    publisher = safe_get_text(xp(".//tei:publisher", ".//publisher"))

    # 6. Series IDNO
    series_idno = safe_get_text(xp(".//tei:idno", ".//idno"))

    # 7. Series Title
    source_title = safe_get_text(xp(".//tei:title", ".//title"))

    return {
        "head": head,
        "idno": idno,
        "origDate": origDate,
        "ueberlieferung": ueberlieferung,
        "transcript": ", ".join(transcribers),
        "tagging": ", ".join(taggers),
        "publisher": publisher,
        "series_idno": series_idno,
        "source_title": source_title,
    }

def main():
    ap = argparse.ArgumentParser(description="Extrahiert Header-Infos (inkl. Überlieferungsträger & Überlieferung) aus TEI/XML in Excel.")
    ap.add_argument("input_xml", type=Path, help="Eingabe TEI/XML Datei")
    ap.add_argument("output_xlsx", type=Path, help="Ausgabe Excel Datei")
    args = ap.parse_args()

    print(f"Lese Datei: {args.input_xml} ...")

    parser = etree.XMLParser(remove_blank_text=True, recover=True)
    try:
        tree = etree.parse(str(args.input_xml), parser)
    except Exception as e:
        print(f"Fehler beim Parsen der XML: {e}")
        return

    root = tree.getroot()

    # Zuerst mit TEI-Namespace
    doc_divs = root.xpath("//tei:div[@type='document']", namespaces=NS)
    # Fallback ohne Namespace
    if not doc_divs:
        doc_divs = root.xpath("//div[@type='document']")

    print(f"{len(doc_divs)} Dokumente gefunden. Schreibe Excel...")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TEI Metadaten"

    # Kopfzeile
    ws.append([label for _, label in FIELDS])
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Datenzeilen
    for idx, div in enumerate(doc_divs, start=1):
        try:
            info = extract_header_info_from_div(div)
            row = [idx] + [info[field] for field, _ in FIELDS if field != "index"]
            ws.append(row)
        except Exception as e:
            print(f"Fehler bei Dokument {idx}: {e}")
            ws.append([idx, "FEHLER"])

    # Spalte C (Idno / Überlieferungsträger) breiter und mit Zeilenumbruch
    col_c = ws.column_dimensions['C']
    col_c.width = 60
    for row in ws.iter_rows(min_col=3, max_col=3, min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical='top')

    # Spalte E (Überlieferung) etwas breiter und mit Zeilenumbruch
    col_e = ws.column_dimensions['E']
    col_e.width = 40
    for row in ws.iter_rows(min_col=5, max_col=5, min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical='top')

    wb.save(str(args.output_xlsx))
    print(f"Fertig! Excel gespeichert: {args.output_xlsx}")

if __name__ == "__main__":
    main()
