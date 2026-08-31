import os
import re
import pandas as pd
from lxml import etree

# ==========================================
# KONFIGURATION
# ==========================================
EXCEL_FILE = r'C:\Temp\Repositories\QZH_anabaptist\titles_tradition.xlsx'       # Pfad zu deiner Excel-Datei
XML_FOLDER = r'C:\Temp\Repositories\QZH_anabaptist\input' # Pfad zu dem Ordner mit den XML-Dateien

# Namespace für TEI-Dokumente
NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

def process_tei_files():
    # 1. Excel-Datei einlesen
    # header=None stellt sicher, dass wir keine Zeilen überspringen.
    # Spalte A = Index 0, Spalte B = Index 1, Spalte C = Index 2
    print("Lese Excel-Datei ein...")
    try:
        df = pd.read_excel(EXCEL_FILE, header=None)
    except Exception as e:
        print(f"Fehler beim Lesen der Excel-Datei: {e}")
        return

    # Dictionary aufbauen: { '5355196': {'A': 'Inhalt A', 'B': 'Inhalt B'} }
    excel_data = {}
    for index, row in df.iterrows():
        valA = row.iloc[0]
        valB = row.iloc[1]
        valC = row.iloc[2]
        
        # Prüfen, ob Spalte C (die ID) befüllt ist
        if pd.notna(valC):
            # ID als reinen Text extrahieren (verhindert Kommazahlen wie "5355196.0")
            c_id = str(valC).replace('.0', '').strip()
            
            # Überspringen, falls in Spalte C das Wort "ID" (als Tabellenkopf) steht
            if c_id.lower() == 'id' or c_id == '':
                continue
                
            excel_data[c_id] = {'A': valA, 'B': valB}
            
    # Set mit allen Excel-IDs (um später abzugleichen, welche nicht gefunden wurden)
    unmatched_ids = set(excel_data.keys())
    
    if not os.path.exists(XML_FOLDER):
        print(f"Der Ordner {XML_FOLDER} existiert nicht.")
        return

    print("Überprüfe XML-Dateien...")
    
    # 2. Durch alle XML-Dateien iterieren
    for filename in os.listdir(XML_FOLDER):
        if not filename.endswith('.xml'):
            continue
            
        filepath = os.path.join(XML_FOLDER, filename)
        
        try:
            # XML parsen (Beibehaltung der Struktur und Stylesheets)
            parser = etree.XMLParser(remove_blank_text=False)
            tree = etree.parse(filepath, parser)
            root = tree.getroot()
        except Exception as e:
            print(f"Fehler beim Parsen von {filename}: {e}")
            continue
            
        # 3. ID aus dem XML extrahieren
        # Sucht das <idno> Element innerhalb von <msIdentifier>
        idno_elements = root.xpath('.//tei:msIdentifier/tei:idno', namespaces=NS)
        if not idno_elements:
            continue
            
        source_attr = idno_elements[0].get('source', '')
        match = re.search(r'ID=(\d+)', source_attr)
        
        if match:
            xml_id = match.group(1)
            
            # 4. Abgleich mit der Excel-Datei
            if xml_id in excel_data:
                unmatched_ids.discard(xml_id) # ID im XML gefunden!
                data = excel_data[xml_id]
                modified = False
                
                # --- MUTATION 1: Spalte A (filiation) einfügen ---
                valA = data['A']
                if pd.notna(valA) and str(valA).strip():
                    textLang_elements = root.xpath('.//tei:msItem/tei:textLang', namespaces=NS)
                    if textLang_elements:
                        textLang = textLang_elements[0]
                        
                        # Neues Element erzeugen
                        new_fil = etree.Element('{http://www.tei-c.org/ns/1.0}filiation', type="current")
                        new_fil.text = str(valA).strip()
                        
                        # Formatierung/Einrückung kopieren, damit das XML sauber bleibt
                        new_fil.tail = textLang.tail if textLang.tail else '\n              '
                        
                        # Direkt nach <textLang> einfügen
                        textLang.addnext(new_fil)
                        modified = True
                        
                # --- MUTATION 2: Spalte B in <head> überschreiben ---
                valB = data['B']
                # Nur ausführen, falls Spalte B explizit befüllt ist
                if pd.notna(valB) and str(valB).strip():
                    # Sucht exakt das <head>, das ein direktes Folge-Element von <msIdentifier> ist
                    head_elements = root.xpath('.//tei:msIdentifier/following-sibling::tei:head', namespaces=NS)
                    if head_elements:
                        head = head_elements[0]
                        head.text = str(valB).strip()
                        modified = True
                        
                # 5. Speichern, falls es Änderungen gab
                if modified:
                    # XML-Deklaration wie <?xml version='1.0' encoding='utf-8'?> erhalten
                    tree.write(filepath, encoding='utf-8', xml_declaration=True, pretty_print=False)
                    print(f"   [+] Aktualisiert: {filename}")

    # 6. Auswertung im Terminal ausgeben
    print("\n" + "="*50)
    print("ZUSAMMENFASSUNG")
    print("="*50)
    if unmatched_ids:
        print(f"WARNUNG: {len(unmatched_ids)} IDs aus dem Excel wurden in KEINER XML-Datei gefunden:")
        for unmatched_id in sorted(unmatched_ids):
            print(f" - {unmatched_id}")
    else:
        print("Erfolg: Alle IDs aus dem Excel wurden in den XML-Dateien gefunden und verarbeitet!")

if __name__ == "__main__":
    process_tei_files()