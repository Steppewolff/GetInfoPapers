# This Python script fetchs papers fields information from Academic APIs.
import requests
import csv
import time
import tkinter as tk
from tkinter import filedialog
from xml.etree import ElementTree as ET

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Bot/0.1)"}

def extract_plain_text_from_element(elem):
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
                abstract = " ".join(
                    extract_plain_text_from_element(elem)
                    for elem in abstract_elem.findall(".//AbstractText")
                ).strip() if abstract_elem is not None else ""

                title_elem = root.find(".//ArticleTitle")
                title = extract_plain_text_from_element(title_elem) if title_elem is not None else ""

                year = root.findtext(".//PubDate/Year", default="") or ""
                month = root.findtext(".//PubDate/Month", default="") or ""
                journal = root.findtext(".//Journal/Title", default="") or ""

                authors = root.findall(".//AuthorList/Author")
                authors_list = []
                for author in authors:
                    lastname = author.findtext("LastName", "")
                    initials = author.findtext("Initials", "")
                    full = f"{lastname} {initials}".strip()
                    if full:
                        authors_list.append(full)
                authors_str = "; ".join(authors_list)

                cite = f"{authors_str}. {title}. {journal}. {year};{month}." if authors_list else ""

                pub_date_parts = [year, month]
                pub_date = "-".join(p.zfill(2) for p in pub_date_parts if p).strip("-")

                link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"

                return title, abstract, year, month, journal, authors_str, cite, pub_date, link
    return None

def get_from_europe_pmc(doi):
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:{doi}&format=json"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        results = res.json().get("resultList", {}).get("result", [])
        if results:
            r = results[0]
            title = r.get("title", "")
            abstract = r.get("abstractText", "")
            year = r.get("pubYear", "")
            month = r.get("pubMonth", "")
            journal = r.get("journalTitle", "")
            authors = r.get("authorString", "")
            cite = f"{authors}. {title}. {journal}. {year};{month}." if authors else ""
            pub_date = "-".join([year, month.zfill(2)]) if year and month else year or ""
            link = f"https://doi.org/{doi}"

            return title, abstract, year, month, journal, authors, cite, pub_date, link
    return None

def get_from_crossref(doi):
    url = f"https://api.crossref.org/works/{doi}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        data = res.json().get("message", {})
        title = data.get("title", [""])[0]
        abstract = data.get("abstract", "")
        if abstract:
            abstract = abstract.replace("<jats:p>", "").replace("</jats:p>", "").strip()
        year = str(data.get("issued", {}).get("date-parts", [[None]])[0][0] or "")
        month = str(data.get("issued", {}).get("date-parts", [[None, None]])[0][1] or "")
        journal = data.get("container-title", [""])[0]
        authors = data.get("author", [])
        author_list = []
        for a in authors:
            given = a.get("given", "")
            family = a.get("family", "")
            full = f"{family} {given}".strip()
            if full:
                author_list.append(full)
        authors_str = "; ".join(author_list)
        cite = f"{authors_str}. {title}. {journal}. {year};{month}." if author_list else ""
        pub_date = "-".join([year, month.zfill(2)]) if year and month else year or ""
        link = f"https://doi.org/{doi}"

        return title, abstract, year, month, journal, authors_str, cite, pub_date, link
    return None

def get_from_semantic_scholar(doi):
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=title,abstract,year,venue,authors"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        data = res.json()
        title = data.get("title", "")
        abstract = data.get("abstract", "")
        year = str(data.get("year", "")) if data.get("year") else ""
        month = ""
        journal = data.get("venue", "")
        authors_list = data.get("authors", [])
        author_names = [a['name'] for a in authors_list if 'name' in a]
        authors_str = "; ".join(author_names)
        cite = f"{authors_str}. {title}. {journal}. {year};{month}." if author_names else ""
        pub_date = year
        link = f"https://doi.org/{doi}"

        return title, abstract, year, month, journal, authors_str, cite, pub_date, link
    return None

def get_article_info(doi):
    for source in [get_from_pubmed, get_from_europe_pmc, get_from_crossref, get_from_semantic_scholar]:
        try:
            result = source(doi)
            if result and any(result):
                return [doi] + list(result)
        except Exception as e:
            print(f"Error al consultar {source.__name__} para {doi}: {e}")
        time.sleep(1)
    return [doi] + [""] * 9  # 9 campos extra además del DOI

def fetch_article_info(dois):
    results = [get_article_info(doi) for doi in dois]
    with open("output.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["DOI", "Title", "Abstract", "Year", "Month", "Journal", "Authors", "Cite", "Pub_Date", "Link"])
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