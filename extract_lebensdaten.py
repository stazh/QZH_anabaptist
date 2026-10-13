#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Editorial-Anmerkungen mit '(15' oder '(16' in eine CSV exportieren.

Aufruf:
    python extract_lebensdaten.py "eingabe.xml" "lebensdaten.csv"
    python extract_lebensdaten.py "XML-Ordner" "lebensdaten.csv"

Bei einem Ordner: alle darin enthaltenen XML-Dateien, ohne Unterordner.
Auch die Endung .XML wird erkannt. Dateien werden nach Dateinamen sortiert.
Bei einer unlesbaren oder fehlerhaften XML-Datei wird abgebrochen, bevor
die CSV geschrieben wird. Die Fehlermeldung nennt die betroffene Datei.
Eine bereits vorhandene Ausgabe-CSV wird bei erfolgreicher Verarbeitung ersetzt.
Keine Zusatzpakete erforderlich. Die XML-Dateien werden nicht verändert.
CSV: drei Spalten, Semikolon als Trennzeichen, UTF-8 mit BOM für Excel.
Die dritte Spalte (Quelldatei) enthält den XML-Dateinamen ohne Ordnerpfad.
Ein Treffer pro Anmerkung, in Dokumentreihenfolge; Wiederholungen bleiben.
Gesucht wird wörtlich im gesamten Anmerkungstext (auch in Unterelementen).
Dies ist keine inhaltliche Erkennung von Lebensdaten.

Name: unmittelbar vorangehendes persName-Geschwisterelement, sofern
dazwischen nur Leerraum steht. Andernfalls die letzten zwei durch Leerraum
getrennten Wörter vor der Anmerkung innerhalb desselben Elternelements.
Dabei werden XML-Tags und die Inhalte vorheriger note-Elemente ignoriert.
Bei weniger als zwei Wörtern werden die vorhandenen Wörter ausgegeben.
Anmerkungen und Namen werden als Text ohne XML-Tags ausgegeben;
mehrfacher Leerraum und Zeilenumbrüche werden zu einem Leerzeichen.
"""

import argparse
import csv
from pathlib import Path
import xml.etree.ElementTree as ET


def local_name(element):
    return element.tag.rsplit('}', 1)[-1]


def normalize(text):
    return ' '.join(text.split())


def source_text(element):
    """Text ohne eingeschobene Anmerkungen, aber mit deren Folgetext."""
    if local_name(element) == 'note':
        return ''
    parts = [element.text or '']
    for child in element:
        parts.append(source_text(child))
        parts.append(child.tail or '')
    return ''.join(parts)


def extract_rows(root):
    # Für jedes Kind den unmittelbar vorangehenden Kontext bestimmen.
    contexts = {}
    for parent in root.iter():
        preceding = parent.text or ''
        previous = None
        for child in parent:
            if local_name(child) == 'note' and child.get('type') == 'editorial':
                direct = (previous is not None
                          and local_name(previous) == 'persName'
                          and not (previous.tail or '').strip())
                if direct:
                    name = normalize(''.join(previous.itertext()))
                else:
                    name = ' '.join(preceding.split()[-2:])
                contexts[child] = (name, direct)
            preceding += source_text(child) + (child.tail or '')
            previous = child

    for note in root.iter():
        if note not in contexts:
            continue
        text = ''.join(note.itertext())
        if '(15' in text or '(16' in text:
            name, direct = contexts[note]
            yield name, normalize(text), direct


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('eingabe', type=Path, help='Pfad zu einer XML-Datei oder einem Ordner')
    parser.add_argument('ausgabe', type=Path, nargs='?',
                        help='CSV-Pfad (Standard: DATEINAME_lebensdaten.csv bzw. lebensdaten.csv im Eingabeordner)')
    args = parser.parse_args()
    if args.eingabe.is_dir():
        try:
            files = sorted((p for p in args.eingabe.iterdir()
                            if p.is_file() and p.suffix.lower() == '.xml'),
                           key=lambda p: (p.name.casefold(), p.name))
        except OSError as error:
            parser.exit(1, f'Ordner kann nicht gelesen werden: {error}\n')
        if not files:
            parser.error('Der Ordner enthält keine XML-Dateien (Unterordner werden nicht durchsucht).')
        output = args.ausgabe or args.eingabe / 'lebensdaten.csv'
    elif args.eingabe.is_file():
        files = [args.eingabe]
        output = args.ausgabe or args.eingabe.with_name(args.eingabe.stem + '_lebensdaten.csv')
    else:
        parser.error(f'Datei oder Ordner nicht gefunden: {args.eingabe}')
    if any(path.resolve() == output.resolve() for path in files):
        parser.error('Die Ausgabe darf keine der Eingabedateien überschreiben.')

    rows = []
    for path in files:
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as error:
            parser.exit(1, f'Fehler in {path}: {error}\nCSV wurde nicht geschrieben.\n')
        rows.extend((name, text, direct, path.name)
                    for name, text, direct in extract_rows(root))
    try:
        with output.open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.writer(handle, delimiter=';')
            writer.writerow(['Name_oder_Woerter', 'Anmerkung', 'Quelldatei'])
            writer.writerows((name, text, filename) for name, text, _, filename in rows)
    except OSError as error:
        parser.exit(1, f'Fehler: {error}\n')
    direct = sum(row[2] for row in rows)
    print(f'{len(files)} XML-Datei(en) verarbeitet; {len(rows)} Treffer exportiert: {output}')
    print(f'{direct} mit direkt vorangehendem persName; {len(rows) - direct} mit Wortkontext.')
    missing = sum(not row[0] for row in rows)
    if missing:
        print(f'Hinweis: Bei {missing} Treffern fehlt vorangehender Text; Spalte 1 bleibt leer.')


if __name__ == '__main__':
    main()
