import re
from pathlib import Path

def aktualisiere_tei_header(ordner_pfad):
    # Den Ordnerpfad als Path-Objekt definieren
    xml_ordner = Path(ordner_pfad)

    # 1. NEUER Regex zum Finden des kompletten <origDate> Elements
    # Sucht nach: <origin> gefolgt von <origDate when="...">
    # und akzeptiert entweder ein selbstschließendes Tag (/>) oder Inhalt plus </origDate>.
    date_pattern = re.compile(r'<origin>\s*(<origDate\s+when="[^"]+"(?:>.*?</origDate>|/>))\s*</origin>', re.DOTALL)

    # 2. Regex zum Finden des exakten Einfügeorts:
    # Sucht nach dem schließenden </msIdentifier>, gefolgt von Whitespace und dem <head> Tag.
    head_pattern = re.compile(r'(</msIdentifier>\s*)(<head>.*?</head>)', re.DOTALL)

    # Alle XML-Dateien im Zielordner durchlaufen
    for datei_pfad in xml_ordner.glob("*.xml"):
        with open(datei_pfad, 'r', encoding='utf-8') as f:
            content = f.read()

        # Überspringen, falls <msContents> bereits existiert (Schutz vor doppelter Ausführung)
        if "<msContents>" in content:
            print(f"Übersprungen (bereits bearbeitet): {datei_pfad.name}")
            continue

        # Komplettes <origDate>-Element extrahieren
        date_match = date_pattern.search(content)
        if not date_match:
            print(f"Übersprungen (kein passendes <origDate> in <origin> gefunden): {datei_pfad.name}")
            continue

        # Dies enthält nun entweder <origDate when="1609-09-02"/> oder <origDate when="1568-08-10">ca.</origDate>
        orig_date_element = date_match.group(1)

        # Den neuen Block zusammenbauen
        # \1 entspricht dem </msIdentifier> + Whitespace
        # \2 entspricht dem kompletten <head>...</head> Block
        neuer_block = (
            r"\1\2" +
            "\n          <msContents>\n" +
            "            <msItem>\n" +
            "              <textLang>Deutsch</textLang>\n" +
            f'              <filiation type="original">{orig_date_element}</filiation>\n' +
            "            </msItem>\n" +
            "          </msContents>"
        )

        # Den neuen Block in den Content einfügen (genau 1x)
        neuer_content, anzahl_ersetzungen = head_pattern.subn(neuer_block, content, count=1)

        if anzahl_ersetzungen > 0:
            # Datei mit der Anpassung überschreiben
            with open(datei_pfad, 'w', encoding='utf-8') as f:
                f.write(neuer_content)
            print(f"Erfolgreich aktualisiert: {datei_pfad.name}")
        else:
            print(f"Übersprungen (Einfügepunkt <head> nach <msIdentifier> nicht gefunden): {datei_pfad.name}")

if __name__ == "__main__":
    # Pfad zum Ordner
    ziel_ordner = r"C:\Temp\Repositories\QZH_anabaptist\input"
    
    # Skript ausführen
    aktualisiere_tei_header(ziel_ordner)