# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "bs4",
#     "lxml",
#     "pydantic",
# ]
# ///

from bs4 import BeautifulSoup as BS
import lxml
from pathlib import Path
from pydantic import BaseModel

#Trouver le fichier html

repertoire = Path(".").resolve()

print(repertoire)
if "matde" in str(repertoire):
    dossier = list(repertoire.glob("*"))[6]
else:
    dossier = list(repertoire.glob("*"))[9]


print(list(dossier.glob("*.html")))

if "matde" in str(dossier):
    fichier = list(dossier.glob("*"))[1]
fichier = list(dossier.glob("*"))[0]
print(fichier)



code_html = fichier.read_text(encoding="utf-8")
len(code_html)
code_html[:200]

# BS

soupe = BS(code_html, features="html.parser")
ma_table = soupe.find("div", attrs={"role": "table"})
#print(ma_table)

#print(ma_table.find_all("div", attrs={"role": "none"}))

# Entête du tableau
head = []
for th in ma_table.find_all("th"):
    span = th.find("span", title=True)
    if span:
        head.append(span["title"])

print(head)

# corps du tableau

corps = ma_table.find("div", attrs={"role": "rowgroup"})
lignes = corps.find_all("tr")
#print(lignes[0])
#print(lignes[-1])
#print(len(lignes))

ligne_test = lignes[5]
print(ligne_test)

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
    contenu : list[Circuits]
    url : str
    description : str

tds = ligne_test.find_all("td")
assert len(tds) == 9

print(tds[0].text)
print(tds[1].text)
print(tds[2].text)
print(tds[3].text)
print(tds[4].text)
print(tds[5].text)
print(tds[6].text)
print(tds[7].text)
print(tds[8].text)

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

print(parse_ligne(ligne_test))

resultat = ParseResult(
    contenu = [parse_ligne(ligne) for ligne in lignes],
    url = "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020/data",
    description = "Récupération de la liste des circuits"
)

sauvegarde = Path(".") / "circuits.json"
if not sauvegarde.exists():
    sauvegarde.write_text(resultat.model_dump_json())

def main() -> None:
    print("Hello from scraping.py!")


if __name__ == "__main__":
    main()
