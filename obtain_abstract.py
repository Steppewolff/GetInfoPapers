# This Python script fetchs papers abstract information from Academic APIs.
import requests
import csv
import time
import tkinter as tk
from tkinter import filedialog
import os
from xml.etree import ElementTree as ET

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Bot/0.1)"}

def extract_plain_text_from_element(elem):
    """Convierte un nodo XML (incluyendo etiquetas anidadas como <i>) en texto plano."""
    parts = [elem.text or ""]
    for subelem in elem:
        parts.append(extract_plain_text_from_element(subelem))
        if subelem.tail:
            parts.append(subelem.tail)
    return ''.join(parts).strip()

def get_from_pubmed(doi):
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={doi}[DOI]&retmode=json"
    search_res = requests.get(search_url, headers=HEADERS)
    if search_res.status_code == 200:
        idlist = search_res.json().get("esearchresult", {}).get("idlist", [])
        if idlist:
            pmid = idlist[0]
            fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
            fetch_res = requests.get(fetch_url, headers=HEADERS)
            if fetch_res.status_code == 200:
                root = ET.fromstring(fetch_res.text)

                abstract_elem = root.find(".//Abstract")
                if abstract_elem is not None:
                    abstract_parts = []
                    for elem in abstract_elem.findall(".//AbstractText"):
                        abstract_parts.append(extract_plain_text_from_element(elem))
                    abstract = " ".join(abstract_parts).strip()
                else:
                    abstract = "No disponible"

                title_elem = root.find(".//ArticleTitle")
                title = extract_plain_text_from_element(title_elem) if title_elem is not None else "No disponible"

                return title, abstract
    return None

def get_from_europe_pmc(doi):
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:{doi}&format=json"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        results = data.get("resultList", {}).get("result", [])
        if results:
            title = results[0].get("title", "No disponible")
            abstract = results[0].get("abstractText", "No disponible")
            return title, abstract
    return None

def get_from_crossref(doi):
    url = f"https://api.crossref.org/works/{doi}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json().get("message", {})
        title = data.get("title", ["No disponible"])[0]
        abstract = data.get("abstract", None)
        if abstract:
            abstract = abstract.replace("<jats:p>", "").replace("</jats:p>", "").strip()
        else:
            abstract = "No disponible"
        return title, abstract
    return None

def get_from_semantic_scholar(doi):
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=title,abstract"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        title = data.get("title", "No disponible")
        abstract = data.get("abstract", "No disponible")
        return title, abstract
    return None

def get_article_info(doi):
    for source in [get_from_pubmed, get_from_europe_pmc, get_from_crossref, get_from_semantic_scholar]:
        try:
            result = source(doi)
            if result and all(result):
                return doi, result[0], result[1]
        except Exception as e:
            print(f"Error al consultar {source.__name__} para {doi}: {e}")
        time.sleep(1)
    return doi, "No disponible", "No disponible"

def fetch_article_info(dois):
    results = [get_article_info(doi) for doi in dois]
    with open("output.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["DOI", "Title", "Abstract"])
        writer.writerows(results)
    print("✅ Exportado a output.csv")

def select_csv_and_get_dois():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Selecciona un archivo CSV con DOIs",
        filetypes=[("CSV files", "*.csv")]
    )
    if not file_path:
        print("❌ No se seleccionó archivo.")
        return []

    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader)
        doi_index = None
        for i, h in enumerate(headers):
            if "doi" in h.lower():
                doi_index = i
                break

        if doi_index is None:
            print("❌ No se encontró una columna de DOIs en el archivo.")
            return []

        return [row[doi_index].strip() for row in reader if len(row) > doi_index and row[doi_index].strip()]

if __name__ == '__main__':
    DOIS = select_csv_and_get_dois()
    if DOIS:
        fetch_article_info(DOIS)