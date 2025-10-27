# python
from bs4 import BeautifulSoup
import lxml

path = r"c:\Users\matde\Documents\Cours\M2\S1\Projet\Projet_WebScraping\Page HTML\Formula 1 World Championship (1950 - 2024).html"

with open(path, 'r', encoding='utf-8') as file:
    content = file.read()

soup = BeautifulSoup(content, 'lxml')

print("Verification que la page est parse : " + str(soup)[:200])

def tableau(page ):
    Tableau_liste = page.find_all('table', class_='table')
    return Tableau_liste

assert tableau(soup) is not None, "Aucun tableau trouve"

print("Verification des tableaus : " + str(tableau(soup)))