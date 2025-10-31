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
from datetime import datetime

# --- 1. Ouvrir la page avec Selenium ---
def recupere_page_selenium(url: str) -> str:
    """Ouvre une page Kaggle avec Safari, scrolle jusqu’à charger tout le tableau, et retourne le HTML complet."""
    print(f"🌐 Ouverture de : {url}")
    driver = webdriver.Safari(service=Service())
    driver.get(url)

    try:
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='table']")))

        table_div = driver.find_element(By.CSS_SELECTOR, "div[role='table']")
        last_height = driver.execute_script("return arguments[0].scrollHeight", table_div)

        # Scroll progressif pour charger toutes les lignes
        while True:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", table_div)
            time.sleep(1.5)
            new_height = driver.execute_script("return arguments[0].scrollHeight", table_div)
            if new_height == last_height:
                break
            last_height = new_height

        print("✅ Fin du scroll dans la table.")

        code_html = driver.page_source
        return code_html

    finally:
        driver.quit()

# --- 4. Parser avec BeautifulSoup ---

def extraction_table(page: str) -> str:
    """Extraction du code source de la balise principale contenant la table"""
    soupe = BS(page, "html.parser")
    table = soupe.find("div", attrs={"role": "table"})
    if not table:
        raise ValueError("❌ Aucune table trouvée dans la page")
    return table

def extraction_lignes(table) -> list:
    """Extraction des lignes du tableau"""
    corps = table.find("div", attrs={"role": "rowgroup"})
    if not corps:
        return []
    return corps.find_all("tr")

# --- 7. Modèles Pydantic ---
class Circuits(BaseModel):
    circuitId: str
    circuitRef: str
    circuitName: str
    circuitLocation: str
    circuitCountry: str
    lat: str
    lng: str
    alt: str
    lien: str

class ConstructorResults(BaseModel):
    constructorResultsId: str
    raceId: str
    constructorId: str
    constructorPoints: int
    status: str
    
class ConstructorStandings(BaseModel):
    constructorStandingId: str
    raceId: str
    constructorId: str
    points: int
    constructorPosition: str
    positionText: str
    constructorWins: str

class Constructors(BaseModel):
    constructorId: str
    constructorRef: str
    constructorName: str
    constructorNationality: str
    lien_constructors: str

class DriverStandings(BaseModel):
    driverStandingId: str
    raceId: str
    driverId: str
    driverPoints: int
    driverPosition: str
    driverPositionText: str
    driverWins: int

class Drivers(BaseModel):
    driverId: str
    driverRef: str
    driverNumber: str
    driverCodeName: str
    driverForename: str
    driverSurname: str
    driverDob: str
    driverNationality: str
    lien_drivers: str

class LapTimes(BaseModel):
    raceId: str
    driverId: str
    lapNumber: str
    lapPosition: str
    lapTime: str
    lapMilliseconds: int

class PitStops(BaseModel):
    raceId: str
    driverId: str
    stopNumber: str
    lapNumber: str
    PStime: str
    PSduration: int
    PSmilliseconds: int

class Qualifiying(BaseModel):
    qualifyId: str
    raceId: str
    driverId: str
    constructorId: str
    driverNumber: str
    position: str
    timeQ1: str
    timeQ2: str
    timeQ3: str

class Races(BaseModel):
    raceId: str
    year: str
    round: str
    circuitId: str
    circuitName: str
    circuitDate: str
    circuitLap: str
    lien_circuits: str
    fp1Date: str
    fp1Time: str

class Results(BaseModel):
    resultId: str
    raceId: str
    driverId: str
    constructorId: str
    driverNumber: str
    gridPosition: str
    finalPosition: str
    finalPositionText: str
    positionOrder: str
    Finalpoints: int

class Seasons(BaseModel):
    year: str
    lien_saisons: str

class SprintResults(BaseModel):
    resultId: str
    raceId: str
    driverId: str
    constructorId: str
    driverNumber: str
    gridPosition: str
    finalPosition: str
    finalPositionText: str
    positionOrder: str
    Finalpoints: int

class Statuts(BaseModel):
    statusId: str
    status: str


class ParseResult(BaseModel):
    contenu: list[Circuits]
    url: str
    description: str

# Dictionnaire qui mappe les noms de dataset à la classe correspondante
TABLE_CLASSES = {
    "circuits": Circuits,
    "constructorResults": ConstructorResults,
    "constructorStandings": ConstructorStandings,
    "constructors": Constructors,
    "driverStanding": DriverStandings,
    "drivers": Drivers,
    "lapTimes": LapTimes,
    "pitStop": PitStops,
    "qualifying": Qualifiying,
    "races": Races,
    "results": Results,
    "seasons": Seasons,
    "sprintResults" : SprintResults,
    "statuts": Statuts
}

# --- 9. Parser toutes les lignes ---
def parse_ligne(ligne, model_cls: type[BaseModel]):
    """Parse une ligne <tr> en fonction du modèle Pydantic"""
    tds = [td.text.strip() for td in ligne.find_all("td")]
    try:
        return model_cls(*tds)
    except Exception as e:
        print(f"⚠️ Ligne ignorée ({e})")
        return None

# --- 10. Sauvegarde ---
def serialise(nom_fichier: str, contenu: list[BaseModel]):
    chemin = Path(".") / nom_fichier
    json_data = json.dumps([o.model_dump() for o in contenu if o], indent=2)
    chemin.write_text(json_data, encoding="utf-8")
    print(f"✅ {len(contenu)} lignes sauvegardées dans {chemin.name}")

def main():
    urls = {
        "circuits": "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020/data",
        "constructorResults": "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020?select=constructor_results.csv",
        "constructorStandings": "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020?select=constructor_standings.csv",
        "constructors": "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020?select=constructors.csv",
        "driverStanding": "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020?select=driver_standings.csv",
        "drivers": "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020?select=drivers.csv",
        "lapTimes": "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020?select=lap_times.csv",
        "pitStop": "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020?select=pit_stops.csv",
        "qualifying": "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020?select=qualifying.csv",
        "races": "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020?select=races.csv",
        "results": "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020?select=results.csv",
        "seasons": "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020?select=seasons.csv",
        "sprintResults" : "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020?select=sprint_results.csv",
        "statuts": "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020?select=status.csv"
    }

    for name, url in urls.items():
        model_cls = TABLE_CLASSES.get(name)
        if not model_cls:
            print(f"⏩ Classe inconnue pour {name}, ignorée.")
            continue

        page = recupere_page_selenium(url)
        table = extraction_table(page)
        lignes = extraction_lignes(table)

        print(f"🔎 {len(lignes)} lignes détectées pour {name}")

        objets = [parse_ligne(ligne, model_cls) for ligne in lignes]
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        serialise(f"{name}_{date_str}.json", objets)

        time.sleep(1)  # éviter de spammer Kaggle



if __name__ == "__main__":
    main()
