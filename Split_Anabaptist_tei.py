#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Segmentiert eine lange XML mit <div type="document"> in viele TEI-Dateien.

Verbesserungen in dieser Version (v5):
- FIX: ECHTE VERSCHIEBUNG. Wenn ein Name vor einer <note> gefunden wird, 
  wird der <persName>-Tag physisch vor die Note verschoben.
  (Vorher blieb der Tag hinter der Note und zog den Text mit sich).
- FIX: Stopword-Logik und Backtracking (aus v3/v4 übernommen).
"""

from pathlib import Path
import re
import argparse
from typing import Optional, Tuple
from copy import deepcopy
from lxml import etree

TEI_NS = "http://www.tei-c.org/ns/1.0"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

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

# Wörter, die signalisieren, dass das Wort davor KEIN Teil des Namens ist.
STOPWORDS = {
    "und", "oder", "aber", "sondern", "denn", "doch",
    "vnnd", "oder", "aber", # Historisch
    "der", "die", "das", "dem", "den", "des", "ein", "eine", "einer", "eines",
    "von", "zu", "in", "im", "am", "auf", "bei", "mit", "nach", "für", "über",
    "dass", "da", "weil", "wenn", "als", "wie",
    "herr", "frau", "meister", "meyster", "doktor", "doctor" 
}

def to_iso_date(date_str: str) -> Optional[str]:
    """Erwartet z.B. '1542 Oktober 25'."""
    if not date_str:
        return None
    s_norm = re.sub(r"\s+", " ", date_str.strip())
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s_norm):
        return s_norm
    tokens = re.split(r"[.\s,;/\-]+", s_norm)
    toks = [t for t in tokens if t]
    if len(toks) < 2:
        return None

    def monthnum(tok: str) -> Optional[str]:
        return MONTHS.get(tok.lower())

    if len(toks) >= 3 and toks[0].isdigit() and len(toks[0]) == 4 and monthnum(toks[1]) and toks[2].isdigit():
        y, m, d = toks[0], monthnum(toks[1]), toks[2].zfill(2)
        return f"{y}-{m}-{d}"
    if len(toks) >= 3 and toks[0].isdigit() and monthnum(toks[1]) and toks[2].isdigit() and len(toks[2]) == 4:
        d, m, y = toks[0].zfill(2), monthnum(toks[1]), toks[2]
        return f"{y}-{m}-{d}"
    if len(toks) >= 2 and toks[0].isdigit() and len(toks[0]) == 4 and monthnum(toks[1]):
        y, m = toks[0], monthnum(toks[1])
        return f"{y}-{m}-01"
    return None

def clean_vorlage(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    t = re.sub(r"^\s*vorlage\s*:\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bstazh\b", "StAZH", t, flags=re.IGNORECASE)
    t = re.sub(r"\bStAZH\s*,\s*", "StAZH ", t)
    return t.strip()

def tei_el(tag, **attrib):
    return etree.Element(f"{{{TEI_NS}}}{tag}", attrib)

def tei_sub(parent, tag, text=None, **attrib):
    el = etree.SubElement(parent, f"{{{TEI_NS}}}{tag}", attrib)
    if text is not None:
        el.text = text
    return el

def build_header(head_text: Optional[str],
                 series_idno: Optional[str],
                 ms_idno: Optional[str],
                 iso_date: Optional[str],
                 qgts_nr: Optional[str] = None) -> etree._Element:
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
    respStmt_series = tei_sub(seriesStmt, "respStmt")
    tei_sub(respStmt_series, "persName", "Tobias Jammerthal")
    tei_sub(respStmt_series, "resp", "Herausgeberschaft")
    tei_sub(seriesStmt, "idno", series_idno or "")

    sourceDesc = tei_sub(fileDesc, "sourceDesc")
    msDesc = tei_sub(sourceDesc, "msDesc")
    msIdentifier = tei_sub(msDesc, "msIdentifier")
    tei_sub(msIdentifier, "idno", ms_idno or "")
    tei_sub(msDesc, "head", head_text or "")

    history = tei_sub(msDesc, "history")
    if iso_date:
        origin = tei_sub(history, "origin")
        tei_sub(origin, "origDate", None, **{"when": iso_date})

    if qgts_nr:
        additional = tei_sub(msDesc, "additional")
        listBibl = tei_sub(additional, "listBibl")
        tei_sub(listBibl, "head", "Edition")
        bibl_outer = tei_sub(listBibl, "bibl")
        bibl_inner = tei_sub(bibl_outer, "bibl")
        ref_el = tei_sub(
            bibl_inner, "ref", "QGTS",
            **{"target": "https://qzh.sources-online.org/exist/apps/qzh/literaturverzeichnis.html"}
        )
        if ref_el is not None:
            ref_el.tail = f", Bd. 5, Nr. {qgts_nr}"

    encodingDesc = tei_sub(teiHeader, "encodingDesc")
    editorialDecl = tei_sub(encodingDesc, "editorialDecl")
    tei_sub(editorialDecl, "p", None)

    profileDesc = tei_sub(teiHeader, "profileDesc")
    tei_sub(profileDesc, "textClass", None, **{"default": "false"})

    return teiHeader

def extract_first_text(el) -> Optional[str]:
    if el is None:
        return None
    return "".join(el.itertext()).strip()

def fix_inline_persnames(p_el: etree._Element):
    """
    Sucht vor <persName/> nach Wörtern.
    Strategie:
    1. Container suchen (Note überspringen).
    2. Wenn gefunden: 
       - Neuen <persName> Tag erstellen.
       - Diesen Tag AN DER STELLE des Textes einfügen (also vor die Note!).
       - Alten Tag löschen.
    """
    WORD = r'[^\W\d_]+(?:-[^\W\d_]+)?'
    NAME_FLEX_RE = re.compile(rf'(?:({WORD})(\s+))?({WORD})(\s*)$', flags=re.UNICODE)

    # Hilfsfunktion, die jetzt Analyse-Daten zurückgibt statt nur Text
    def analyze_container_text(text: str) -> Optional[Tuple[str, int, str]]:
        if not text: return None
        m = NAME_FLEX_RE.search(text)
        if not m: return None
        
        w1, ws1, w2, ws_end = m.groups()
        take_two = False
        if w1 and w1.lower() not in STOPWORDS:
            take_two = True
        
        if take_two:
            name_text = f"{w1}{ws1}{w2}"
            cut_pos = m.start(0)
        else:
            if w2.lower() in STOPWORDS: return None
            name_text = w2
            cut_pos = m.start(3)
            
        return (name_text, cut_pos, ws_end)

    # Durch alle leeren persNames iterieren
    # Wir machen eine Liste, da wir den Tree verändern werden
    for pers in list(p_el.xpath('.//*[local-name()="persName"]')):
        if pers.text and pers.text.strip():
            continue
        
        parent = pers.getparent()
        if parent is None: continue
        
        # --- Container Suche ---
        container = None
        use_tail = False
        curr = pers.getprevious()
        
        while True:
            if curr is None:
                container = parent
                use_tail = False
                break
            
            # Hat das Element Text im Tail?
            if curr.tail and curr.tail.strip():
                container = curr
                use_tail = True
                break
            
            # Überspringen
            tag_local = etree.QName(curr).localname
            if tag_local in ['note', 'pb', 'lb', 'cb', 'gap']:
                curr = curr.getprevious()
                continue
            
            # Sonstiges Element: nehmen wir dessen Tail
            container = curr
            use_tail = True
            break
            
        # Wenn wir nichts gefunden haben
        if container is None: continue

        # --- Analyse ---
        text_to_check = container.tail if use_tail else container.text
        result = analyze_container_text(text_to_check)
        
        if result:
            name_text, cut_pos, ws_end = result
            
            # --- DOM OPERATION: MOVE AND REPLACE ---
            
            # 1. Neuen Tag erstellen (Kopie der Attribute)
            new_pers = deepcopy(pers)
            new_pers.text = name_text
            # Der Whitespace, der NACH dem Namen kam, wird zum Tail des neuen Tags
            new_pers.tail = ws_end 
            
            # 2. Text im Container abschneiden
            remaining_text = text_to_check[:cut_pos]
            
            if use_tail:
                container.tail = remaining_text
                # Einfügen: NACH dem Container
                parent_of_container = container.getparent()
                # Index finden
                idx = parent_of_container.index(container)
                parent_of_container.insert(idx + 1, new_pers)
            else:
                container.text = remaining_text
                # Einfügen: Als ERSTES Kind des Containers (der Parent ist)
                container.insert(0, new_pers)
                
            # 3. Alten Tag löschen
            parent.remove(pers)

def fix_inline_placenames(p_el: etree._Element) -> None:
    # Hier lassen wir die einfache Logik, da Ortsnamen selten von Notes getrennt sind.
    # Falls doch, müsste man die Logik von oben spiegeln.
    WORD_RE = re.compile(r'([^\W\d_]+(?:-[^\W\d_]+)?)(\s*)$', flags=re.UNICODE)

    def extract_last_word_preserve_space(container, use_tail: bool) -> Optional[str]:
        txt = (container.tail if use_tail else container.text) or ''
        m = WORD_RE.search(txt)
        if not m:
            return None
        token, ws_after = m.groups()
        new_txt = txt[: m.start(1)] + ws_after
        if use_tail:
            container.tail = new_txt
        else:
            container.text = new_txt
        return token

    for pn in list(p_el.xpath('.//*[local-name()="placeName" and not(normalize-space())]')):
        parent = pn.getparent()
        if parent is None: continue
        prev = pn.getprevious()
        token = extract_last_word_preserve_space(prev, True) if prev is not None else None
        if not token:
            token = extract_last_word_preserve_space(parent, False)
        if token:
            pn.text = token

def build_tei_tree(head_text, series_idno, ms_idno, iso_date, content_nodes, editorial_notes, qgts_nr=None):
    root = etree.Element("{%s}TEI" % TEI_NS, nsmap={None: TEI_NS, "xsi": XSI_NS})
    teiHeader = build_header(head_text, series_idno, ms_idno, iso_date, qgts_nr)
    root.append(teiHeader)

    text = tei_sub(root, "text")
    body = tei_sub(text, "body")
    div = tei_sub(body, "div")

    for node in content_nodes:
        node_copy = deepcopy(node)
        if etree.QName(node_copy).localname == "p":
            try:
                fix_inline_persnames(node_copy)
                fix_inline_placenames(node_copy)
            except Exception:
                pass
        div.append(node_copy)

    if editorial_notes:
        back = tei_sub(text, "back")
        for note in editorial_notes:
            note_div = tei_sub(back, "div")
            p = tei_sub(note_div, "p")
            p.text = note.text
            for child in note:
                child_copy = deepcopy(child)
                p.append(child_copy)

    return root

def process(input_xml: Path, outdir: Path, prefix: str = "QZH"):
    outdir.mkdir(parents=True, exist_ok=True)
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(input_xml), parser)
    divs = tree.xpath('//*[local-name()="div" and @type="document"]')

    for idx, d in enumerate(divs, start=115):
        head_el = d.xpath('.//*[local-name()="head"]')
        if head_el:
            head_copy = deepcopy(head_el[0])
            for n in list(head_copy.xpath('.//*[local-name()="note" and @type="editorial"]')):
                parent = n.getparent()
                if parent is not None:
                    parent.remove(n)
            head_text = extract_first_text(head_copy) or ""
        else:
            head_text = ""

        vorlage_el = d.xpath('.//*[local-name()="div" and @type="vorlage"]')
        original_el = d.xpath('.//*[local-name()="div" and @type="original"]')
        ms_idno = ""
        if vorlage_el:
            ms_idno = clean_vorlage(extract_first_text(vorlage_el[0]) or "")
        elif original_el:
            ms_idno = clean_vorlage(extract_first_text(original_el[0]) or "")

        content_xpath = './/*[(local-name()="p" or local-name()="pb" or (local-name()="head" and @type="Originalsprache")) and not(ancestor::*[local-name()="p"])]'
        content_nodes = d.xpath(content_xpath)

        iso_when = None
        qgts_nr = None
        src_with_n = d.xpath('.//*[local-name()="div" and @type="source" and @n][1]')
        if src_with_n:
            src = src_with_n[0]
        else:
            src_any = d.xpath('.//*[local-name()="div" and @type="source"][1]')
            src = src_any[0] if src_any else None
        
        if src is not None:
            date_attr = src.get('date') or ''
            iso_when = to_iso_date(date_attr)
            qgts_nr = (src.get('n') or '').strip() or None

        editorial_notes = []
        for n in d.xpath('.//*[local-name()="note" and @type="editorial"]'):
            if any((anc.tag.endswith("head")) for anc in n.iterancestors()):
                editorial_notes.append(n)

        series_idno = f"{prefix}_{idx}"
        tei_root = build_tei_tree(head_text, series_idno, ms_idno, iso_when, content_nodes, editorial_notes, qgts_nr)
        tei_tree = etree.ElementTree(tei_root)
        
        pi = etree.ProcessingInstruction(
            "xml-stylesheet",
            "type='text/xsl' href='../../Ressourcen/Stylesheet.xsl'"
        )
        tei_tree.getroot().addprevious(pi)

        filename = f"{prefix}_{idx}.xml"
        out_path = outdir / filename
        tei_tree.write(str(out_path), encoding="UTF-8", xml_declaration=True, pretty_print=True)
        print(f"Geschrieben: {out_path}")

def main():
    ap = argparse.ArgumentParser(description="Segmentiert TEI/XML nach <div type='document'>.")
    ap.add_argument("input", type=Path, help="Pfad zur Eingabe-XML")
    ap.add_argument("outdir", type=Path, help="Ausgabe-Ordner")
    ap.add_argument("--prefix", default="QZH", help="Dateinamen-Präfix")
    args = ap.parse_args()
    process(args.input, args.outdir, args.prefix)

if __name__ == "__main__":
    main()