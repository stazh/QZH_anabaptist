import os
import xml.etree.ElementTree as ET

def extract_and_build_places(input_folder, output_filename):
    TEI_NS = "http://www.tei-c.org/ns/1.0"
    XML_NS = "http://www.w3.org/XML/1998/namespace"
    
    ET.register_namespace('', TEI_NS)
    ns = {'tei': TEI_NS}
    
    # Dictionary für die Orte: { 'place_id': set('Name1', 'Name2', ...) }
    places = {}

    for filename in os.listdir(input_folder):
        if not filename.endswith('.xml'):
            continue
            
        filepath = os.path.join(input_folder, filename)
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # 1. Versuche die idno (z.B. QZH_050) aus den Metadaten zu extrahieren
            idno_element = root.find('.//tei:seriesStmt/tei:idno', ns)
            if idno_element is not None and idno_element.text:
                doc_idno = " ".join(idno_element.text.split())
            else:
                # Fallback, falls keine idno vorhanden ist: Dateiname ohne Endung nutzen
                doc_idno = os.path.splitext(filename)[0]
            
            # 2. Suche alle placeName-Elemente strikt innerhalb von <text>
            # Wir nutzen enumerate ab 1, um das $pos Verhalten aus XQuery zu simulieren
            place_names = root.findall('.//tei:text//tei:placeName', ns)
            
            for pos, place_node in enumerate(place_names, start=1):
                # Textinhalt analog zu fn:normalize-space() bereinigen
                raw_text = "".join(place_node.itertext())
                name = " ".join(raw_text.split())
                
                if not name:
                    continue
                    
                # Attribut 'ref' auslesen
                ref = place_node.get('ref')
                
                if ref:
                    # Führendes '#' entfernen, falls vorhanden
                    place_id = ref.lstrip('#')
                else:
                    # Generiere automatische ID: idno + Position (z.B. QZH_050_12)
                    place_id = f"{doc_idno}_{pos}"
                    
                if place_id not in places:
                    places[place_id] = set()
                places[place_id].add(name)
                    
        except ET.ParseError as e:
            print(f"Warnung: Datei '{filename}' konnte nicht geparst werden ({e})")

    # 3. Vorbereiten der alphabetischen Sortierung nach Ortsnamen
    # Wir wandeln das Dictionary in eine Liste um und sortieren die Ortsnamen intern
    sorted_places_list = []
    for pid, names_set in places.items():
        sorted_names = sorted(list(names_set))
        sorted_places_list.append((pid, sorted_names))
        
    # Die Hauptliste alphabetisch nach dem allerersten Namenseintrag sortieren
    # (case-insensitive via .lower() für saubere A-Z Reihung)
    sorted_places_list.sort(key=lambda x: x[1][0].lower())

    # 4. Ziel-XML aufbauen
    tei = ET.Element(f'{{{TEI_NS}}}TEI', attrib={f'{{{XML_NS}}}id': 'places', 'type': 'Ort'})
    
    teiHeader = ET.SubElement(tei, f'{{{TEI_NS}}}teiHeader')
    fileDesc = ET.SubElement(teiHeader, f'{{{TEI_NS}}}fileDesc')
    titleStmt = ET.SubElement(fileDesc, f'{{{TEI_NS}}}titleStmt')
    ET.SubElement(titleStmt, f'{{{TEI_NS}}}title').text = "Quellen zur Zürcher Geschichte: Ortsdaten"
    
    publicationStmt = ET.SubElement(fileDesc, f'{{{TEI_NS}}}publicationStmt')
    ET.SubElement(publicationStmt, f'{{{TEI_NS}}}p').text = "Publication Information"
    
    sourceDesc = ET.SubElement(fileDesc, f'{{{TEI_NS}}}sourceDesc')
    ET.SubElement(sourceDesc, f'{{{TEI_NS}}}p').text = "Information about the source"

    standOff = ET.SubElement(tei, f'{{{TEI_NS}}}standOff')
    listPlace = ET.SubElement(standOff, f'{{{TEI_NS}}}listPlace')

    # 5. XML-Einträge aus der sortierten Liste generieren
    for place_id, sorted_names in sorted_places_list:
        n_attr = ", ".join(sorted_names)
        
        place_node = ET.SubElement(listPlace, f'{{{TEI_NS}}}place', attrib={f'{{{XML_NS}}}id': place_id, 'n': n_attr})
        
        for name in sorted_names:
            pn = ET.SubElement(place_node, f'{{{TEI_NS}}}placeName', attrib={'type': 'main'})
            pn.text = name
            
        # Geodaten-Extraktion und Validierung für IDs, die mit LOC_ beginnen
        if place_id.startswith("LOC_"):
            parts = place_id[4:].split('_')
            if len(parts) == 2:
                try:
                    lat = float(parts[0])
                    lon = float(parts[1])
                    # Prüfen, ob es gültige Koordinaten sind (entspricht dem XQuery Regex-Gedanken)
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        location = ET.SubElement(place_node, f'{{{TEI_NS}}}location')
                        ET.SubElement(location, f'{{{TEI_NS}}}geo').text = f"{parts[0]} {parts[1]}"
                except ValueError:
                    # Überspringen, falls sich die ID unerwartet nicht in Zahlen umwandeln lässt
                    pass

    # XML Formatierung einrücken
    if hasattr(ET, 'indent'):
        ET.indent(tei, space="    ", level=0)

    # In Zieldatei schreiben
    tree = ET.ElementTree(tei)
    tree.write(output_filename, encoding='utf-8', xml_declaration=True, method="xml")
    print(f"Erfolgreich {len(places)} einzigartige Orte extrahiert und alphabetisch in '{output_filename}' geschrieben.")

if __name__ == "__main__":
    # Verzeichnis der XML-Quelldateien
    EINGABE_ORDNER = r"C:\Temp\Repositories\QZH_anabaptist\input"
    AUSGABE_DATEI = "places_output.xml"
    
    if not os.path.exists(EINGABE_ORDNER):
        print(f"Fehler: Der Ordner '{EINGABE_ORDNER}' wurde nicht gefunden.")
    else:
        extract_and_build_places(EINGABE_ORDNER, AUSGABE_DATEI)