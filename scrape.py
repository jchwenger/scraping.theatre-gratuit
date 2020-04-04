import os
import bs4
import regex
import urllib3
import certifi
from time import sleep
from bs4 import BeautifulSoup


def main():
    url = "https://theatregratuit.com/"
    http = urllib3.PoolManager(cert_reqs="CERT_REQUIRED", ca_certs=certifi.where())
    pages, all_a_with_href = find_all_pages(url, http)
    out_dir = "theatregratuit-epubs"
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)
    all_epub_links = []
    n_epubs = 0
    for a in all_a_with_href:
        if a.text == "epub":
            all_epub_links.append(a)
            n_epubs += 1
    print(f"found {n_epubs} epubs")
    saving_epub = 1
    for a in all_epub_links:
        fname = a["href"].split("/")[-1]
        oname = os.path.join(out_dir, fname)
        if not os.path.isfile(oname):
            print(f"scraping: {saving_epub}/{n_epubs} | {fname}")
            epub = get_page(a["href"], http)
            with open(oname, "wb") as o:
                o.write(epub)
            sleep(0.4)
        else:
            print(f"already downloaded: {saving_epub}/{n_epubs} | {fname}")
        saving_epub += 1

    print(f"done, {len(os.listdir(out_dir))} files in {out_dir}")


def get_soup(url, http):
    r = http.request("GET", url)
    return BeautifulSoup(r.data, "html.parser")


def get_page(url, http):
    r = http.request("GET", url)
    return r.data


def find_next_page_link(all_a_with_href, index):
    page_re = regex.compile(f"page.*{index}", regex.IGNORECASE)
    for a in reversed(all_a_with_href):
        if regex.search(page_re, a.text):
            print("found additional page:", a.text, a["href"])
            return a["href"]
    return False


def find_all_pages(url, http):
    index = 1
    pages = []
    print("starting with first page...")
    pages.append(get_soup(url, http))
    all_a_with_href = pages[0].find_all("a", href=True)
    index += 1
    next_link = find_next_page_link(all_a_with_href, index)
    while next_link:
        new_page = get_soup(f"{url}/{next_link}", http)
        pages.append(new_page)
        all_a_with_href.extend(new_page.find_all("a", href=True))
        index += 1
        next_link = find_next_page_link(all_a_with_href, index)
    print("-" * 40)
    return pages, all_a_with_href


if __name__ == "__main__":
    main()
