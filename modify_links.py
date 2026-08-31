from pathlib import Path
import re
import shutil
from lxml import etree

# ============================================================
# KONFIGURATION
# ============================================================

# Ordner mit deinen XML-Dateien
INPUT_DIR = Path(r"C:\Temp\Repositories\QZH_anabaptist\input")

# Nur Dateien direkt im Ordner bearbeiten:
RECURSIVE = False

# Falls auch Unterordner durchsucht werden sollen:
# RECURSIVE = True

# Sicherheitskopien anlegen?
# Aus datei.xml wird zusätzlich datei.xml.bak
MAKE_BACKUP = True

# ============================================================
# AB HIER NORMALER SKRIPTTEIL
# ============================================================

TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}


def transform_file_in_place(input_path: Path) -> int:
    parser = etree.XMLParser(
        remove_blank_text=False,
        recover=False
    )

    tree = etree.parse(str(input_path), parser)

    hl_elements = tree.xpath(
        "//tei:hl[@to][tei:Hyperlink][contains(@to, 'fwb-online.de')]",
        namespaces=NS
    )

    count = 0

    for hl in hl_elements:
        url = hl.get("to")
        parent = hl.getparent()

        if parent is None or not url:
            continue

        index = parent.index(hl)
        old_tail = hl.tail or ""

        # Fall 1:
        # Direkt nach </hl> folgt ein Klammertext,
        # z. B. (Frühneuhochdeutsches Wörterbuch)
        match = re.match(r"^(\s*)\(([^()]*)\)(.*)$", old_tail, flags=re.DOTALL)

        if match:
            link_text = match.group(2).strip() or url
            new_tail = match.group(3)
        else:
            # Fall 2:
            # Kein Klammertext folgt direkt nach </hl>;
            # dann wird die URL selbst als Linktext verwendet.
            link_text = url
            new_tail = old_tail

        bibl = etree.Element(f"{{{TEI_NS}}}bibl")
        ref = etree.SubElement(bibl, f"{{{TEI_NS}}}ref")
        ref.set("target", url)
        ref.text = link_text

        bibl.tail = new_tail

        parent[index] = bibl
        count += 1

    # Nur speichern, wenn tatsächlich etwas geändert wurde
    if count > 0:
        if MAKE_BACKUP:
            backup_path = input_path.with_suffix(input_path.suffix + ".bak")
            shutil.copy2(input_path, backup_path)

        tree.write(
            str(input_path),
            encoding="UTF-8",
            xml_declaration=True,
            pretty_print=False
        )

    return count


def main() -> None:
    if RECURSIVE:
        xml_files = INPUT_DIR.rglob("*.xml")
    else:
        xml_files = INPUT_DIR.glob("*.xml")

    total_files = 0
    total_links = 0

    for input_file in xml_files:
        # Sicherungskopien selbst nicht erneut bearbeiten
        if input_file.name.endswith(".bak"):
            continue

        changed_links = transform_file_in_place(input_file)

        if changed_links > 0:
            print(f"{input_file.name}: {changed_links} Link(s) direkt in der Datei transformiert")
            total_files += 1
            total_links += changed_links
        else:
            print(f"{input_file.name}: keine passenden FWB-Links gefunden")

    print()
    print(f"Fertig. Geänderte Dateien: {total_files}")
    print(f"Transformierte Links insgesamt: {total_links}")

    if MAKE_BACKUP:
        print("Sicherungskopien wurden als .xml.bak angelegt.")


if __name__ == "__main__":
    main()