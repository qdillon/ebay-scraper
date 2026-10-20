#!/usr/bin/env python3
"""ebay-dl.py: scrape eBay search results into JSON (or CSV).

Usage:
    python ebay-dl.py --search "garden tools"
    python ebay-dl.py "garden tools" --csv
    python ebay-dl.py --search "garden tools" --pages-dir practice-pages
"""
import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

FIELDS = ['name', 'price', 'status', 'shipping', 'free_returns', 'items_sold']
NUM_PAGES = 10
HEADERS = {'User-Agent': 'Mozilla/5.0'}
STATUS_RE = re.compile(
    r'\b(Brand New|Certified Refurbished|Seller Refurbished|Refurbished|'
    r'Pre-?Owned|Open Box|For Parts or Not Working|Used|New)\b', re.I)
MONEY_RE = re.compile(r'\$\s*([\d,]+)(?:\.(\d{1,2}))?')


def money_to_cents(text):
    """Convert the first dollar amount in text to integer cents (no floats).

    >>> money_to_cents('$54.99 to $79.99')
    5499
    >>> money_to_cents('$1,250')
    125000
    >>> money_to_cents('$5.5')
    550
    >>> money_to_cents('no price') is None
    True
    """
    m = MONEY_RE.search(text or '')
    if not m:
        return None
    dollars = int(m.group(1).replace(',', ''))
    cents = int((m.group(2) or '0').ljust(2, '0'))
    return dollars * 100 + cents


def parse_shipping(text):
    """Return shipping cost in cents from a card's text, or None.

    >>> parse_shipping('Free delivery')
    0
    >>> parse_shipping('+$4.25 shipping')
    425
    >>> parse_shipping('$7.00 delivery')
    700
    >>> parse_shipping('nothing here') is None
    True
    """
    if re.search(r'free\s+(shipping|delivery)', text, re.I):
        return 0
    m = re.search(r'\+?\s*(\$\s*[\d,]+(?:\.\d{1,2})?)\s*(?:shipping|delivery)',
                  text, re.I)
    return money_to_cents(m.group(1)) if m else None


def parse_items_sold(text):
    """Return the integer count in text like '1,234 sold', or None.

    >>> parse_items_sold('1,234 sold')
    1234
    >>> parse_items_sold('5+ sold')
    5
    >>> parse_items_sold('Free returns') is None
    True
    """
    m = re.search(r'([\d,]+)\+?\s+sold\b', text, re.I)
    return int(m.group(1).replace(',', '')) if m else None


def text_of(tag):
    return tag.get_text(' ', strip=True) if tag else None


def parse_card(card):
    """Extract one listing dict from a result card, or None if not a real item."""
    title_tag = card.select_one(
        '.s-item__title, .s-card__title, [role="heading"], h3')
    name = text_of(title_tag)
    if not name:
        return None
    name = re.sub(r'^New Listing\s*', '', name, flags=re.I)
    name = re.sub(r'\s*Opens in a new window or tab$', '', name).strip()
    if not name or name.lower() == 'shop on ebay':
        return None

    card_text = card.get_text(' ', strip=True)

    price_tag = card.select_one('.s-item__price, .s-card__price')
    price = money_to_cents(text_of(price_tag) or '')

    status = None
    sub = card.select_one('.SECONDARY_INFO, .s-card__subtitle')
    if sub:
        status = text_of(sub).split('·')[0].strip() or None
    if status is None:
        m = STATUS_RE.search(card_text.replace(name, ''))
        status = m.group(1) if m else None

    shipping_tag = card.select_one(
        '.s-item__shipping, .s-item__logisticsCost, .s-card__shipping')
    shipping = parse_shipping(text_of(shipping_tag) or '')
    if shipping is None:
        shipping = parse_shipping(card_text)

    # True: "Free returns"; False: other return text; None: no return info
    if re.search(r'free returns', card_text, re.I):
        free_returns = True
    elif re.search(r'return', card_text, re.I):
        free_returns = False
    else:
        free_returns = None
    items_sold = parse_items_sold(card_text)

    return {'name': name, 'price': price, 'status': status,
            'shipping': shipping, 'free_returns': free_returns,
            'items_sold': items_sold}


def extract_items(html):
    """Take an HTML string (response.text or a saved file) and return a list
    of listing dicts.

    >>> html = ('<ul><li class="s-item"><div class="s-item__title">Trowel</div>'
    ...   '<span class="s-item__price">$11.95</span>'
    ...   '<span class="SECONDARY_INFO">Brand New</span>'
    ...   '<span class="s-item__shipping">Free delivery</span>'
    ...   '<span>Free returns</span><span>12 sold</span></li></ul>')
    >>> extract_items(html)[0]['price']
    1195
    >>> extract_items(html)[0]['free_returns']
    True
    """
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.select('li.s-item, li.s-card, div.s-card')
    items = []
    for card in cards:
        if card.find_parent(['li', 'div'], class_=re.compile(r's-(item|card)$')):
            continue  # skip nested duplicates
        item = parse_card(card)
        if item:
            items.append(item)
    return items


def looks_blocked(html):
    return bool(re.search(r'robot|captcha|verify yourself|Pardon Our Interruption',
                          html[:5000], re.I))


def fetch_page(search, page):
    response = requests.get(
        'https://www.ebay.com/sch/i.html',
        params={'_nkw': search, '_pgn': page},
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    return response.text


def collect(search, pages_dir=None, num_pages=NUM_PAGES):
    all_items = []
    for page in range(1, num_pages + 1):
        if pages_dir:
            path = Path(pages_dir) / f'page-{page}.html'
            html = path.read_text(encoding='utf-8')
        else:
            html = fetch_page(search, page)
            if looks_blocked(html):
                sys.exit('eBay returned a robot check. Stop live requests and '
                         'use --pages-dir practice-pages instead.')
        items = extract_items(html)
        if not items and not pages_dir:
            print(f'Page {page}: no listings found; stopping.', file=sys.stderr)
            break
        print(f'Page {page}: {len(items)} items', file=sys.stderr)
        all_items.extend(items)
        if not pages_dir and page < num_pages:
            time.sleep(1.5)  # be polite
    return all_items


def main():
    parser = argparse.ArgumentParser(description='Scrape eBay search results.')
    parser.add_argument('term', nargs='?', help='search term (positional form)')
    parser.add_argument('--search', help='search term')
    parser.add_argument('--pages-dir',
                        help='folder with page-1.html..page-10.html to use '
                             'instead of live requests')
    parser.add_argument('--csv', action='store_true',
                        help='write CSV instead of JSON')
    args = parser.parse_args()

    search = args.search or args.term
    if not search:
        parser.error('a search term is required (--search "term")')

    items = collect(search, args.pages_dir)
    safe = search.replace('/', '_')
    if args.csv:
        with open(f'{safe}.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(items)
        print(f'Wrote {len(items)} items to {safe}.csv', file=sys.stderr)
    else:
        with open(f'{safe}.json', 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=2)
        print(f'Wrote {len(items)} items to {safe}.json', file=sys.stderr)


if __name__ == '__main__':
    main()
