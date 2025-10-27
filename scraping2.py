# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "bs4",
#     "pydantic",
#     "requests",
#     "selenium",
# ]
# ///

from bs4 import BeautifulSoup as BS
from pydantic import BaseModel
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.safari.service import Service
from selenium.webdriver.safari.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# --- 1. Ouvrir la page avec Selenium ---
url = "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020/data"

driver = webdriver.Safari(service=Service())
driver.get(url)

# --- 2. Attendre que la table soit présente ---
wait = WebDriverWait(driver, 10)  # max 10 secondes
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='table']")))

table_div = driver.find_element(By.CSS_SELECTOR, "div[role='table']")
last_height = driver.execute_script("return arguments[0].scrollHeight", table_div)

while True:
    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", table_div)
    time.sleep(2)

    new_height = driver.execute_script("return arguments[0].scrollHeight", table_div)
    if new_height == last_height:
        break
    last_height = new_height

print("✅ Fin du scroll dans la table.")

# --- 3. Récupérer le HTML complet de la page ---
code_html = driver.page_source
driver.quit()

# --- 4. Parser avec BeautifulSoup ---
soupe = BS(code_html, features="html.parser")
ma_table = soupe.find("div", attrs={"role": "table"})

# --- 5. Entêtes du tableau ---
head = []
for th in ma_table.find_all("th"):
    span = th.find("span", title=True)
    if span:
        head.append(span["title"])
print("Entêtes :", head)

# --- 6. Corps du tableau ---
corps = ma_table.find("div", attrs={"role": "rowgroup"})
lignes = corps.find_all("tr")
print("Nombre de lignes :", len(lignes))

# --- 7. Modèles Pydantic ---
class Circuits(BaseModel):
    circuitId: str
    circuitRef: str
    name: str
    location: str
    country: str
    lat: str
    lng: str
    alt: str
    lien: str

class ParseResult(BaseModel):
    contenu: list[Circuits]
    url: str
    description: str

# --- 8. Fonction de parsing d'une ligne ---
def parse_ligne(ligne: "bs4.element.Tag") -> Circuits:
    tds = ligne.find_all("td")
    assert len(tds) == 9
    return Circuits(
        circuitId = tds[0].text.strip(),
        circuitRef = tds[1].text.strip(),
        name = tds[2].text.strip(),
        location = tds[3].text.strip(),
        country = tds[4].text.strip(),
        lat = tds[5].text.strip(),
        lng = tds[6].text.strip(),
        alt = tds[7].text.strip(),
        lien = tds[8].text.strip()
    )

# --- 9. Parser toutes les lignes ---
resultat = ParseResult(
    contenu=[parse_ligne(ligne) for ligne in lignes],
    url=url,
    description="Récupération de la liste des circuits"
)

# --- 10. Sauvegarde ---
sauvegarde = Path(".") / "circuits2.json"
sauvegarde.write_text(resultat.model_dump_json())
print("Fichier circuits.json créé ✅")

def main() -> None:
    print("Hello from scraping2.py!")


if __name__ == "__main__":
    main()
