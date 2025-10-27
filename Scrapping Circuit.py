# scrapping_f1_kaggle_all.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os
from bs4 import BeautifulSoup

# ============================
# ======= UTILITAIRES ========
# ============================

def normalize_text(text):
    if not text:
        return ""
    return " ".join(text.split()).strip()

# ============================
# ====== EXTRACTION HTML =====
# ============================

def extraire_donnees(html: str):
    """Retourne une liste des éléments ayant role="table"."""
    soup_local = BeautifulSoup(html, 'html.parser')
    elems = soup_local.find_all(attrs={"role": "table"})
    return [str(e) for e in elems]

def extraire_header(table_html: str):
    """Extrait la liste des titres depuis un élément role="table"."""
    soup_local = BeautifulSoup(table_html, 'html.parser')
    header_el = soup_local.find(attrs={"role": "none"})
    if not header_el:
        return []

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
    """Retourne la liste des lignes pour un élément role="table"."""
    soup_local = BeautifulSoup(table_html, 'html.parser')
    rows = []
    header_el = soup_local.find(attrs={"role": "none"})

    def in_header(el):
        return header_el is not None and header_el in getattr(el, "parents", [])

    for rg in soup_local.find_all(attrs={"role": "rowgroup"}):
        row_elems = rg.find_all(attrs={"role": "row"})
        if row_elems:
            for r in row_elems:
                if in_header(r):
                    continue
                tds = r.find_all('td')
                rows.append([normalize_text(td.get_text()) for td in tds])
            continue

        spans = [el for el in rg.find_all('span', recursive=False)]
        if spans:
            for sp in spans:
                if in_header(sp):
                    continue
                tds = sp.find_all('td')
                if tds:
                    rows.append([normalize_text(td.get_text()) for td in tds])
                    continue
                tr = sp.find('tr')
                if tr and not in_header(tr):
                    tds = tr.find_all('td')
                    rows.append([normalize_text(td.get_text()) for td in tds])
                    continue
                text = normalize_text(sp.get_text())
                if text:
                    rows.append([text])
        else:
            trs = rg.find_all('tr')
            for tr in trs:
                if in_header(tr):
                    continue
                tds = tr.find_all('td')
                rows.append([normalize_text(td.get_text()) for td in tds])

    if not rows:
        for tr in soup_local.find_all('tr'):
            if in_header(tr):
                continue
            tds = tr.find_all('td')
            if tds:
                rows.append([normalize_text(td.get_text()) for td in tds])

    rows = [r for r in rows if any(cell.strip() for cell in r)]
    return rows

# ============================
# ===== JSON EXPORT UTILS ====
# ============================

def table_to_json_obj(header, rows):
    if header and rows and all(len(r) == len(header) for r in rows):
        rows_out = [dict(zip(header, r)) for r in rows]
    else:
        rows_out = rows
    return {"header": header, "rows": rows_out, "count": len(rows)}

def export_tables_json(tables_html, dest_path):
    tables_data = []
    for t_html in tables_html:
        hdr = extraire_header(t_html)
        rows = extraire_rows(t_html)
        tables_data.append(table_to_json_obj(hdr, rows))
    with open(dest_path, "w", encoding="utf-8") as jf:
        json.dump({"tables": tables_data}, jf, ensure_ascii=False, indent=2)
    return dest_path

# ============================
# ======= SCROLL UTILS =======
# ============================

def scroll_table_element(driver, table_selector='[role="table"]', scroll_pause_time=1.0, max_attempts=50):
    """Fait défiler l'élément scrollable du tableau jusqu'à ce que tout soit chargé."""
    elem = driver.find_element(By.CSS_SELECTOR, table_selector)
    last_scroll_top = 0
    same_count = 0

    for i in range(max_attempts):
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", elem)
        time.sleep(scroll_pause_time)
        scroll_top = driver.execute_script("return arguments[0].scrollTop", elem)

        if scroll_top == last_scroll_top:
            same_count += 1
            if same_count >= 3:
                print(f"[INFO] Fin du scroll interne après {i+1} tentatives.")
                break
        else:
            same_count = 0
            last_scroll_top = scroll_top

def scroll_to_load_all(driver, scroll_pause_time=1.0, max_attempts=30):
    """Scroll général sur la fenêtre (utile si la table n'est pas dans un conteneur scrollable)."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    same_count = 0

    for i in range(max_attempts):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            same_count += 1
            if same_count >= 3:
                print(f"[INFO] Fin du scroll après {i+1} tentatives (hauteur stable).")
                break
        else:
            same_count = 0
            last_height = new_height

# ============================
# ==== SELENIUM PRINCIPAL ====
# ============================

def recuperer_page_selenium(url: str,
                            headless: bool = True,
                            wait_selector: str = '[role="table"]',
                            timeout: int = 20,
                            reuse_profile: str = None) -> str:
    """Ouvre la page Kaggle, attend le tableau, scrolle jusqu'à la fin et retourne le HTML complet."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    if reuse_profile:
        chrome_options.add_argument(f'--user-data-dir={reuse_profile}')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        wait = WebDriverWait(driver, timeout)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector)))

        # Tentative scroll interne, sinon global
        try:
            scroll_table_element(driver, table_selector=wait_selector, scroll_pause_time=1.0, max_attempts=60)
        except Exception as e:
            print(f"[WARN] Scroll interne échoué ({e}), tentative scroll global...")
            scroll_to_load_all(driver, scroll_pause_time=1.0, max_attempts=40)

        time.sleep(1)
        html = driver.page_source
        return html
    finally:
        driver.quit()

# ============================
# ======= MAIN MULTI URL =====
# ============================

if __name__ == "__main__":
    base_url = "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020/data?select={name}.csv"
    tables_list = [
        "constructor_results",
        "constructor_standings",
        "circuits",
        "constructors",
        "driver_standings",
        "lap_times",
        "drivers",
        "pit_stops",
        "qualifying",
        "races",
        "results",
        "seasons",
        "sprint_results",
        "status",
    ]

    os.makedirs("outputs", exist_ok=True)

    for name in tables_list:
        url = base_url.format(name=name)
        print(f"\n============================")
        print(f"🔗 Scraping : {url}")
        print("============================")

        try:
            rendered_html = recuperer_page_selenium(url, headless=True)
            tables = extraire_donnees(rendered_html)
            if not tables:
                print(f"[WARN] Aucun tableau trouvé pour {name}")
                continue

            dest_path = f"outputs/{name}.json"
            export_tables_json(tables, dest_path)
            print(f"✅ Fichier exporté -> {dest_path}")

        except Exception as e:
            print(f"❌ Erreur pour {name} : {e}")
