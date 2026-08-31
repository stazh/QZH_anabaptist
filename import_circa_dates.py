import os
import re
import pandas as pd
from datetime import datetime, timedelta

# --- Konfiguration ---
EXCEL_DIR = r"C:\Temp\Repositories\QZH_anabaptist"
XML_DIR = r"C:\Temp\Repositories\QZH_anabaptist\input"
EXCEL_FILE = "Daten_ca.xlsx" # <--- HIER WIEDER DEINEN EXCEL-NAMEN EINTRAGEN
EXCEL_PATH = os.path.join(EXCEL_DIR, EXCEL_FILE)

# Monat-Mapping für deutsche Monatsnamen
MONTHS = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4,
    "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
    "oktober": 10, "november": 11, "dezember": 12
}

def get_month_num(month_str):
    month_str = month_str.lower().strip()
    for m_name, m_num in MONTHS.items():
        if m_name in month_str:
            return m_num
    return 1

def parse_date_string(date_cell):
    clean_str = str(date_cell).replace('[', '').replace(']', '').replace('?', '').lower().strip()
    
    year_match = re.search(r'\b(\d{4})\b', clean_str)
    if not year_match:
        return None
    year = int(year_match.group(1))

    # --- Fall 1: "nach" ---
    m = re.search(r'nach\s+([a-zäöü]+)\s+(\d+)', clean_str)
    if m:
        month = get_month_num(m.group(1))
        day = int(m.group(2))
        dt = datetime(year, month, day) + timedelta(days=1)
        return {"type": "single", "date": dt.strftime('%Y-%m-%d')}

    # --- Fall 2: "vor" ---
    m = re.search(r'vor\s+([a-zäöü]+)\s+(\d+)', clean_str)
    if m:
        month = get_month_num(m.group(1))
        day = int(m.group(2))
        dt = datetime(year, month, day) - timedelta(days=1)
        return {"type": "single", "date": dt.strftime('%Y-%m-%d')}

    # --- Fall 3: "nicht vor" ---
    m = re.search(r'([a-zäöü]+)\s+nicht\s+vor\s+(\d+)', clean_str)
    if m:
        month = get_month_num(m.group(1))
        day = int(m.group(2))
        dt = datetime(year, month, day)
        return {"type": "single", "date": dt.strftime('%Y-%m-%d')}

    # --- Fall 4: "zwischen" ---
    m = re.search(r'zwischen\s+([a-zäöü]+)\s+(\d+)', clean_str)
    if m:
        month = get_month_num(m.group(1))
        day = int(m.group(2))
        dt = datetime(year, month, day) + timedelta(days=1)
        return {"type": "single", "date": dt.strftime('%Y-%m-%d')}

    # --- Fall 5: Schrägstrich "/" ---
    m = re.search(r'([a-zäöü]+)\s*/\s*([a-zäöü]+)', clean_str)
    if m:
        month1 = get_month_num(m.group(1))
        return {"type": "single", "date": f"{year}-{month1:02d}"}

    # --- Fall 6: Bindestrich "-" (Range) ---
    m = re.search(r'([a-zäöü]+)\s*-\s*([a-zäöü]+)', clean_str)
    if m:
        month1 = get_month_num(m.group(1))
        month2 = get_month_num(m.group(2))
        return {"type": "range", "from": f"{year}-{month1:02d}", "to": f"{year}-{month2:02d}"}

    # --- Fallback: Nur Jahr und (optional) Monat wie "[1525 November]" ---
    found_month = None
    for m_name, m_num in MONTHS.items():
        if m_name in clean_str:
            found_month = m_num
            break
            
    if found_month:
        return {"type": "single", "date": f"{year}-{found_month:02d}"}
    else:
        return {"type": "single", "date": f"{year}"}

def process_excel():
    print(f"Lese Excel-Datei: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)

    for index, row in df.iterrows():
        xml_filename = str(row.iloc[0]).strip()
        date_cell = str(row.iloc[1]).strip()

        if '[' not in date_cell:
            continue
        
        if not xml_filename.lower().endswith('.xml'):
            xml_filename += '.xml'
            
        xml_filepath = os.path.join(XML_DIR, xml_filename)
        
        if not os.path.exists(xml_filepath):
            print(f"Warnung: Datei {xml_filename} nicht gefunden. Überspringe...")
            continue

        parsed_date = parse_date_string(date_cell)
        if not parsed_date:
            print(f"Warnung: Konnte das Datum in Zeile {index + 2} nicht parsen: '{date_cell}'")
            continue

        # XML Templates generieren
        if parsed_date["type"] == "single":
            msitem_insert = f"""            <msItem>
              <textLang>Deutsch</textLang>
              <filiation type="original"><origDate when="{parsed_date['date']}"/>ca.</filiation>
            </msItem>"""
            history_insert = f"""          <history>
            <origin><origDate when="{parsed_date['date']}">ca.</origDate></origin>
          </history>"""
        else: # range
            msitem_insert = f"""            <msItem>
              <textLang>Deutsch</textLang>
              <filiation type="original"><origDate from="{parsed_date['from']}" to="{parsed_date['to']}"></origDate></filiation>
            </msItem>"""
            history_insert = f"""          <history>
            <origin><origDate from="{parsed_date['from']}" to="{parsed_date['to']}"></origDate></origin>
          </history>"""

        with open(xml_filepath, 'r', encoding='utf-8') as f:
            original_xml_content = f.read()

        xml_content = original_xml_content

        # 1. Entferne eventuell vorhandene leere <history/> Tags (inkl. Zeilenumbrüchen), um Duplikate zu vermeiden
        xml_content = re.sub(r'<history\s*/>\s*', '', xml_content)

        # 2. Prüfen, ob <msContents> existiert
        if re.search(r'<msContents[^>]*>', xml_content):
            # Wenn ja: Füge msItem direkt nach dem öffnenden Tag ein
            xml_content = re.sub(r'(<msContents[^>]*>)', r'\1\n' + msitem_insert, xml_content, count=1)
        else:
            # Wenn nein: Erstelle den ganzen <msContents> Block und füge ihn nach </head> ein
            mscontents_block = f"          <msContents>\n{msitem_insert}\n          </msContents>"
            xml_content = re.sub(r'(</head>)', r'\1\n' + mscontents_block, xml_content, count=1)

        # 3. <history> direkt NACH dem schließenden </msContents> Tag einfügen
        # Da wir oben sicherstellen, dass msContents existiert oder neu erstellt wird, greift dieser Suchbegriff jetzt immer.
        xml_content = re.sub(r'(</msContents>)', r'\1\n' + history_insert, xml_content, count=1)

        # 4. Speichern, falls Änderungen gemacht wurden
        if xml_content != original_xml_content:
            with open(xml_filepath, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            print(f"Erfolgreich aktualisiert: {xml_filename} -> {parsed_date}")
        else:
            print(f"⚠️ Warnung: {xml_filename} wurde nicht verändert (Struktur weicht ab)!")

if __name__ == "__main__":
    process_excel()