# ebay-scraper

`ebay-dl.py` is a command-line program that scrapes eBay search results. Given a
search term, it downloads the first 10 pages of results (with `requests`, a
`User-Agent` header, a timeout, and a pause between pages), extracts each listing
with Beautiful Soup, and saves the listings as JSON (or CSV with `--csv`).

Each listing has these keys; a missing field is stored as `None` (`null` in JSON):

- `name`: item name
- `price`: price in cents (integer; the first price is used for ranges)
- `status`: condition, e.g. "Brand New", "Pre-Owned"
- `shipping`: shipping cost in cents (`0` = free)
- `free_returns`: boolean (`None` if the listing says nothing about returns)
- `items_sold`: integer count sold

Extraction (`extract_items`) takes an HTML string, so it works on live
`response.text` or on saved files. Helper functions have doctests
(`python -m doctest ebay-dl.py`).

## Setup

```
python -m pip install requests beautifulsoup4
```

## Running

Live requests:

```
python ebay-dl.py --search "garden tools"
```

Offline, from saved pages (`page-1.html` ... `page-10.html`):

```
python ebay-dl.py --search "garden tools" --pages-dir practice-pages
```

## Commands used to generate the JSON files in this repo

**Provenance note:** these outputs use **artificial practice data**, not live eBay. They were generated from the instructor-provided `practice-pages/` folder (from `practice-pages.zip`). The listings are identical for every search term; only the filename comes from the term.

```
python ebay-dl.py --search "garden tools" --pages-dir practice-pages
python ebay-dl.py --search "drill press" --pages-dir practice-pages
python ebay-dl.py --search "stuffed animal" --pages-dir practice-pages
```

## CSV (extra credit)

With `--csv`, the output is `SEARCH_TERM.csv` instead of JSON:

```
python ebay-dl.py --search "garden tools" --pages-dir practice-pages --csv
python ebay-dl.py --search "drill press" --pages-dir practice-pages --csv
python ebay-dl.py --search "stuffed animal" --pages-dir practice-pages --csv
```

## Project page

Project page: [eBay scraper project page](https://csci40.rtealwitter.com/projects/02_webscraping/project.html)