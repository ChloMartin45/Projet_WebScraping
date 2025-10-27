# python
from bs4 import BeautifulSoup
import re
import os
import json

path = r"c:\Users\matde\Documents\Cours\M2\S1\Projet\Projet_WebScraping\Page HTML\Formula 1 World Championship (1950 - 2024).html"

with open(path, 'r', encoding='utf-8') as file:
    content = file.read()

# essayer lxml si disponible, sinon fallback sur html.parser
try:
    soup = BeautifulSoup(content, 'lxml')
except Exception:
    soup = BeautifulSoup(content, 'html.parser')

print("Verification que la page est parse : " + str(soup)[:200])

def extraire_donnees(html: str):
    """Retourne une liste des éléments ayant role="table" (ex. <div role="table"> ou <table role="table">)."""
    soup_local = BeautifulSoup(html, 'html.parser')
    elems = soup_local.find_all(attrs={"role": "table"})
    return [str(e) for e in elems]

# exemple d'utilisation : afficher les 50 premiers caractères de chaque élément role="table"
tables = extraire_donnees(content)
print(f"{len(tables)} élément(s) avec role=\"table\" trouvé(s)")
for i, t in enumerate(tables, start=1):
    print(f"Table {i}: {t}")

def normalize_text(text):
    if not text:
        return ""
    return " ".join(text.split()).strip()

def extraire_header(table_html: str):
    """
    Extrait la liste des titres depuis un élément role="table" (HTML en str).
    Comportement demandé :
      - trouver le sous-élément ayant role="none"
      - prendre son <tr> (si présent) et récupérer chaque <th> de ce <tr>
      - pour chaque <th>, retourner le texte contenu dans son <p> si présent, sinon le texte du <th>
    """
    soup_local = BeautifulSoup(table_html, 'html.parser')
    header_el = soup_local.find(attrs={"role": "none"})
    if not header_el:
        return []

    # privilégier le <tr> à l'intérieur du header_el
    tr = header_el.find("tr")
    ths = tr.find_all("th") if tr else header_el.find_all("th")

    headers = []
    for th in ths:
        p = th.find("p")
        if p:
            headers.append(normalize_text(p.get_text()))
        else:
            headers.append(normalize_text(th.get_text()))
    return headers

# utilisation : ne récupérer et afficher que les headers pour chaque element role="table"
tables = extraire_donnees(content)  # conserve la fonction existante qui retourne les éléments role="table" en str
print(f"{len(tables)} élément(s) role=\"table\" trouvé(s) — affichage des headers uniquement")
for i, t in enumerate(tables, start=1):
    hdr = extraire_header(t)
    print(f"Table {i}: header = {hdr}")
    print(len(hdr))

def extraire_rows(table_html: str):
    """
    Retourne la liste des lignes pour un élément role="table".
    - Ignore les <tr> qui sont dans le header (role="none").
    - Garde la logique existante pour rowgroup / span / tr.
    - Filtre les lignes vides.
    """
    soup_local = BeautifulSoup(table_html, 'html.parser')
    rows = []

    # élément header (à ne pas ré-intégrer comme ligne)
    header_el = soup_local.find(attrs={"role": "none"})

    def in_header(el):
        return header_el is not None and header_el in getattr(el, "parents", [])

    # parcourir chaque rowgroup
    for rg in soup_local.find_all(attrs={"role": "rowgroup"}):
        # priorité aux éléments marqués role="row"
        row_elems = rg.find_all(attrs={"role": "row"})
        if row_elems:
            for r in row_elems:
                if in_header(r):
                    continue
                tds = r.find_all('td')
                rows.append([normalize_text(td.get_text()) for td in tds])
            continue

        # sinon, chercher des spans direct enfants (souvent chaque span représente une ligne)
        spans = [el for el in rg.find_all('span', recursive=False)]
        if spans:
            for sp in spans:
                if in_header(sp):
                    continue
                # si le span contient des <td> directement
                tds = sp.find_all('td')
                if tds:
                    rows.append([normalize_text(td.get_text()) for td in tds])
                    continue
                # sinon, si le span contient un <tr>
                tr = sp.find('tr')
                if tr and not in_header(tr):
                    tds = tr.find_all('td')
                    rows.append([normalize_text(td.get_text()) for td in tds])
                    continue
                # fallback : tout le texte du span (une seule cellule)
                text = normalize_text(sp.get_text())
                if text:
                    rows.append([text])

        else:
            # fallback : chercher des <tr> dans le rowgroup
            trs = rg.find_all('tr')
            for tr in trs:
                if in_header(tr):
                    continue
                tds = tr.find_all('td')
                rows.append([normalize_text(td.get_text()) for td in tds])

    # si aucune rowgroup trouvée, essayer d'extraire directement les <tr> du table_html
    if not rows:
        for tr in soup_local.find_all('tr'):
            if in_header(tr):
                continue
            tds = tr.find_all('td')
            if tds:
                rows.append([normalize_text(td.get_text()) for td in tds])

    # filtrer les lignes vides et les single-cells vides
    rows = [r for r in rows if any(cell.strip() for cell in r)]
    return rows

# utilisation : n'afficher que les headers et le nombre de lignes (preview de la 1ère ligne)
tables = extraire_donnees(content)
for i, t in enumerate(tables, start=1):
    hdr = extraire_header(t)
    rows = extraire_rows(t)
    print(f"         lignes trouvées = {len(rows)}")
    if rows:
        print(f"         1ère ligne (cells) = {rows[0]}")
        print(f"         dernière ligne (cells) = {rows[-1]}")

def table_to_json_obj(header, rows):
    """
    Retourne un objet JSON pour un tableau.
    - Si header present et toutes les lignes ont la même longueur, rows -> liste de dicts {header: value}
    - Sinon rows -> liste de listes (cells)
    - count toujours présent
    """
    if header and rows and all(len(r) == len(header) for r in rows):
        rows_out = [dict(zip(header, r)) for r in rows]
    else:
        rows_out = rows
    return {"header": header, "rows": rows_out, "count": len(rows)}

def export_tables_json(tables_html, dest_path=None):
    """
    Prend une liste d'éléments role='table' (HTML strings), construit un JSON
    et écrit dans dest_path (ou même dossier que le fichier source .html).
    Retourne le chemin du fichier écrit.
    """
    tables_data = []
    for t_html in tables_html:
        hdr = extraire_header(t_html)
        rows = extraire_rows(t_html)
        tables_data.append(table_to_json_obj(hdr, rows))

    if dest_path is None:
        base = os.path.splitext(path)[0]
        dest_path = base + ".json"

    with open(dest_path, "w", encoding="utf-8") as jf:
        json.dump({"tables": tables_data}, jf, ensure_ascii=False, indent=2)

    return dest_path

def check_row_counts(tables_html, expected=9, max_examples=10):
    """
    Vérifie que chaque ligne de chaque table a 'expected' colonnes.
    Affiche un résumé et jusqu'à max_examples exemples de lignes problématiques.
    Retourne la liste des problèmes trouvés.
    """
    problems = []
    for ti, t_html in enumerate(tables_html, start=1):
        rows = extraire_rows(t_html)
        for ri, row in enumerate(rows, start=1):
            if len(row) != expected:
                problems.append({
                    "table_index": ti,
                    "row_index": ri,
                    "cols_found": len(row),
                    "preview": row[:expected+2]
                })
                if len(problems) >= max_examples:
                    break
        if len(problems) >= max_examples:
            break

    if not problems:
        print(f"Toutes les lignes ont bien {expected} colonnes.")
    else:
        print(f"{len(problems)} ligne(s) avec un nombre de colonnes != {expected} (affichage jusqu'à {max_examples} exemples) :")
        for p in problems[:max_examples]:
            print(f" Table {p['table_index']} - ligne {p['row_index']}: colonnes={p['cols_found']} preview={p['preview']}")
    return problems

# appel : vérifier avant (ou après) l'export JSON
tables = extraire_donnees(content)
check_row_counts(tables, expected=9, max_examples=20)

# exécution : exporter tous les tableaux trouvés en JSON
tables = extraire_donnees(content)
out = export_tables_json(tables)
print(f"Export JSON créé -> {out}")

