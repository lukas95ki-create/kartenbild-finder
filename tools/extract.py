#!/usr/bin/env python3
"""Robust extractor for PokeZentrum card gallery / secret-rare pages.

Filenames are taken EXACTLY from the HTML (never guessed). Handles both
dash- and underscore-separated schemes, auto-detects the set total, and
tags each card with a category (ex / AR / SAR / SR / UR).

Usage:
  extract.py --total 80 --code M3 --lang Japanisch --name "Munikis Zero" \
             --page URL --out-prefix links/Japanisch-M3 file1.html [file2.html ...]
If --total is omitted it is auto-detected as the dominant set size.
"""
import re, sys, json, html, argparse, collections

UPLOAD_RE = re.compile(r'https://pokezentrum\.de/wp-content/uploads/([^"\'\s?)]+?\.jpg)')
SIZE_SUFFIX = re.compile(r'-\d{2,4}x\d{2,4}\.jpg$')
# number and total separated by - or _ ; total then followed by - or _
NUMTOTAL = re.compile(r'[-_](\d{3})[-_](\d{2,3})[-_]')

def base_name(fn):
    fn = SIZE_SUFFIX.sub('.jpg', fn)
    fn = re.sub(r'-scaled\.jpg$', '.jpg', fn)
    return fn

def categorize(fn):
    s = fn
    # order matters: gold/UR first, then SAR, then SR, then AR
    if re.search(r'[-_](MUR|UR|HR)[-_]', s) or re.search(r'Ultra-Rare-Gold|Hyper-Rare|Gold-Rare|Rainbow|[-_]Gold[-_]', s, re.I):
        return 'UR'
    if re.search(r'[-_]SAR[-_]', s) or re.search(r'Special-Art|Special-Illustration-Rare', s, re.I):
        return 'SAR'
    if re.search(r'[-_]SR[-_]', s) or re.search(r'Full-Art|Ultra-Rare', s, re.I):
        return 'SR'
    if re.search(r'[-_]AR[-_]', s) or re.search(r'Art-Rare|Art-Illustration-Rare|Illustration-Rare', s, re.I):
        return 'AR'
    if re.search(r'[-_]ex(?=[-_.])', s, re.I):
        return 'ex'
    return ''

def name_of(fn, num):
    # take everything before the -NNN- / _NNN- number token
    m = re.search(r'^(.*?)[-_]' + f'{num:03d}' + r'[-_]', fn)
    stem = m.group(1) if m else fn.rsplit('.jpg',1)[0]
    return stem.replace('_', '-')

def load(paths):
    urls = []
    for p in paths:
        with open(p, encoding='utf-8', errors='replace') as f:
            doc = html.unescape(f.read())
        for m in UPLOAD_RE.finditer(doc):
            urls.append(base_name(m.group(1)))
    return urls

def detect_total(urls):
    c = collections.Counter()
    for fn in urls:
        if 'Pokemon-Karte' not in fn and 'Pokemon-Card' not in fn:
            continue
        for nm in NUMTOTAL.finditer(fn):
            c[nm.group(2)] += 1
    return int(c.most_common(1)[0][0]) if c else None

def extract(paths, total, marker=None):
    urls = load(paths)
    if total is None:
        total = detect_total(urls)
    if total is None:
        return None, [], {}
    # accept both 2- and 3-digit total spellings
    total_variants = {f'{total:03d}', f'{total:02d}', str(total)}
    seen = {}
    order = []
    for fn in urls:
        if 'Pokemon-Karte' not in fn and 'Pokemon-Card' not in fn:
            continue
        if marker and marker not in fn:
            continue
        m = NUMTOTAL.search(fn)
        if not m:
            continue
        if m.group(2) not in total_variants:
            continue
        num = int(m.group(1))
        if fn in seen:
            continue
        seen[fn] = num
        order.append(fn)
    return total, order, seen

LEAD_RE = re.compile(r'^(\d{2,3})_(.+)$')
NAME_CUT = re.compile(r'_(SV\d|KP\d|CBB|Karmesin|China|Pokemon-Karte|Pokemon-Card|Basis-Set)', re.I)

def extract_lead(paths, code, marker=None):
    """Early scheme: filename starts with the card number, e.g.
    001_Hoppip_Hoppspross_SV2D_Clay-Burst-Pokemon-Karte.jpg (no total token)."""
    urls = load(paths)
    key = (marker or code).lower()
    seen = {}
    order = []
    for fn in urls:
        m = LEAD_RE.match(fn)
        if not m:
            continue
        if key not in fn.lower():
            continue
        if 'pokemon-karte' not in fn.lower() and 'pokemon-card' not in fn.lower():
            continue
        if fn in seen:
            continue
        seen[fn] = int(m.group(1))
        order.append(fn)
    total = max(seen.values()) if seen else None
    return total, order, seen

def name_of_lead(fn, num, code):
    rest = re.sub(r'^\d{2,3}_', '', fn)
    cut = NAME_CUT.search(rest)
    stem = rest[:cut.start()] if cut else rest.rsplit('.jpg', 1)[0]
    return stem.replace('_', '-').strip('-')

def extract_loose(paths, marker):
    """Fallback for irregular numbering (e.g. Chinese Gem Packs): take every
    card image containing the marker, keep order, number sequentially."""
    urls = load(paths)
    seen = []
    s = set()
    for fn in urls:
        if marker.lower() not in fn.lower():
            continue
        if 'pokemon-karte' not in fn.lower() and 'pokemon-card' not in fn.lower():
            continue
        if 'logo' in fn.lower() or 'booster' in fn.lower() or 'display' in fn.lower():
            continue
        if fn in s:
            continue
        s.add(fn); seen.append(fn)
    return seen

def name_of_loose(fn):
    stem = re.split(r'[-_]\d', fn, 1)[0]
    return stem.replace('_', '-').strip('-')

def build(paths, total, code, marker=None, scheme='auto'):
    if scheme == 'loose':
        order = extract_loose(paths, marker or code)
        cards, known = [], {}
        for i, fn in enumerate(order, 1):
            cat = categorize(fn)
            cards.append([i, name_of_loose(fn), None, cat])
            known[i] = fn
        return {'code': code, 'total': len(order), 'cards': cards, 'known': known,
                'missing': [], 'n_base': len(order), 'n_secret': 0}
    if scheme == 'lead':
        t2, order, seen = extract_lead(paths, code, marker)
        total = total or t2
        cards, known = [], {}
        base = {}
        for fn in order:
            n = seen[fn]
            base.setdefault(n, fn)
        for n in sorted(base):
            fn = base[n]
            cards.append([n, name_of_lead(fn, n, code), None, categorize(fn)])
            known[n] = fn
        missing = [n for n in range(1, (total or 0)+1) if n not in base]
        return {'code': code, 'total': total or 0, 'cards': cards, 'known': known,
                'missing': missing, 'n_base': len(base), 'n_secret': 0}
    total, order, seen = extract(paths, total, marker)
    if total is None:
        return {'code': code, 'total': 0, 'cards': [], 'known': {},
                'missing': [], 'n_base': 0, 'n_secret': 0}
    base = {}      # num -> fn   (num <= total, category '')
    base_notes = []
    secret = []    # list of (num, fn, cat)
    for fn in order:
        num = seen[fn]
        cat = categorize(fn)
        if num <= total and cat in ('', 'ex'):
            if num in base:
                base_notes.append(f'dup base {num}: {fn}')
            else:
                base[num] = fn
        else:
            secret.append((num, fn, cat if cat else 'SR'))
    # resolve base typo collisions
    present = set(base)
    missing = [n for n in range(1, total+1) if n not in present]
    for note in list(base_notes):
        fn = note.split(': ',1)[1]
        if len(missing) == 1:
            slot = missing.pop(0)
            base[slot] = fn
    missing = [n for n in range(1, total+1) if n not in base]
    # assemble cards + known
    cards = []
    known = {}
    for n in range(1, total+1):
        if n in base:
            fn = base[n]
            cat = categorize(fn)
            cards.append([n, name_of(fn, n), None, cat])
            known[n] = fn
    # secret rares: assign keys continuing above total, keep order
    key = max(total, max(base) if base else total)
    used = set(range(1, total+1))
    secret_sorted = sorted(secret, key=lambda t: (t[0], t[1]))
    for num, fn, cat in secret_sorted:
        k = num
        while k in used:
            k += 1000  # avoid collision but keep near real number space
        used.add(k)
        known[k] = fn
        cards.append([k, name_of(fn, num), None, cat])  # cat at index 3 for app filters
    return {'code': code, 'total': total, 'cards': cards, 'known': known,
            'missing': missing, 'n_base': len(base), 'n_secret': len(secret)}

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--total', type=int, default=None)
    ap.add_argument('--code', required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--lang', required=True)
    ap.add_argument('--page', required=True)
    ap.add_argument('--marker', default=None)
    ap.add_argument('--out-prefix', default=None)
    ap.add_argument('files', nargs='+')
    a = ap.parse_args()
    r = build(a.files, a.total, a.code, a.marker)
    r['name'] = a.name; r['lang'] = a.lang; r['page'] = a.page
    print(json.dumps(r, ensure_ascii=False))
