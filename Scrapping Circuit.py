# scrapping_circuit_selenium.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import json
from bs4 import BeautifulSoup

def normalize_text(text):
    if not text:
        return ""
    return " ".join(text.split()).strip()

def extraire_donnees(html: str):
    """Retourne une liste des éléments ayant role="table" (ex. <div role="table"> ou <table role="table">)."""
    soup_local = BeautifulSoup(html, 'html.parser')
    elems = soup_local.find_all(attrs={"role": "table"})
    return [str(e) for e in elems]

def extraire_header(table_html: str):
    """
    Extrait la liste des titres depuis un élément role="table" (HTML en str).
    Comportement : prendre le premier élément ayant role="none", privilégier son <tr> et ses <th>,
    pour chaque <th> retourner le texte du <p> s'il existe, sinon le texte du <th>.
    """
    soup_local = BeautifulSoup(table_html, 'html.parser')
    header_el = soup_local.find(attrs={"role": "none"})  # find -> premier élément
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

def extraire_rows(table_html: str):
    """
    Retourne la liste des lignes pour un élément role="table".
    - Ignore les <tr> qui sont dans le header (premier role="none").
    - Parcourt rowgroup / span / tr comme dans hello.py.
    - Filtre les lignes vides.
    """
    soup_local = BeautifulSoup(table_html, 'html.parser')
    rows = []

    # élément header (premier role="none") à exclure
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

def export_tables_json(tables_html, dest_path="tables_from_live.json"):
    tables_data = []
    for t_html in tables_html:
        hdr = extraire_header(t_html)
        rows = extraire_rows(t_html)
        tables_data.append(table_to_json_obj(hdr, rows))
    with open(dest_path, "w", encoding="utf-8") as jf:
        json.dump({"tables": tables_data}, jf, ensure_ascii=False, indent=2)
    return dest_path

# --- Partie Selenium : récupérer le HTML rendu ---
def recuperer_page_selenium(url: str,
                            headless: bool = True,
                            wait_selector: str = '[role="table"]',
                            timeout: int = 15,
                            reuse_profile: str = None) -> str:
    """
    Ouvre la page dans Chrome via Selenium, attend que wait_selector soit présent,
    puis renvoie le HTML rendu (page_source).
    - headless: True pour exécuter sans fenêtre (sans UI).
    - wait_selector: selector CSS utilisé pour détecter que le contenu principal est chargé.
    - reuse_profile: chemin d'un dossier user-data-dir si tu veux réutiliser une session (cookies, login).
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")  # headless moderne
        chrome_options.add_argument("--disable-gpu")
    # options utiles
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    if reuse_profile:
        # attention : si tu fais cela, utilise un dossier dédié (ne pointe pas sur ton profile chrome principal)
        chrome_options.add_argument(f'--user-data-dir={reuse_profile}')

    # initialise le driver (webdriver-manager gère la version du driver)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)

        # Attendre la présence d'un élément indiquant que le tableau est chargé.
        # Si ton tableau n'a pas role="table", adapte wait_selector.
        wait = WebDriverWait(driver, timeout)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector)))

        # Optionnel : attendre un petit peu supplémentaire si le contenu est lazy-loaded
        time.sleep(1)

        html = driver.page_source
        return html
    finally:
        driver.quit()

# --- Exemple d'utilisation dans ton pipeline ---
if __name__ == "__main__":
    URL = "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020/data?select=circuits.csv"

    # Si tu veux voir la fenêtre Chrome pour déboguer, passe headless=False
    rendered_html = recuperer_page_selenium(URL, headless=False, wait_selector='[role="table"]', timeout=20,
                                            reuse_profile=None)
    # sauvegarde pour inspection
    with open("page_rendue.html", "w", encoding="utf-8") as f:
        f.write(rendered_html)

    # passe le HTML rendu à tes fonctions existantes
    tables = extraire_donnees(rendered_html)
    print(f"Tables trouvées: {len(tables)}")
    if tables:
        print("Header first table:", extraire_header(tables[0]))
        print("Rows count first table:", len(extraire_rows(tables[0])))

    out = export_tables_json(tables, dest_path="tables_live.json")
    print("Export JSON créé ->", out)