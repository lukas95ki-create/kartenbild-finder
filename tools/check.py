#!/usr/bin/env python3
"""Spot-check 3 image URLs per set for reachability and compile
fehlende-bilder.txt (missing source cards + any failed spot-check)."""
import os
import json, subprocess, time, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMGBASE = "https://pokezentrum.de/wp-content/uploads/"

def head(url):
    r = subprocess.run(["curl", "-sS", "-I", "-o", "/dev/null", "-w", "%{http_code}",
                        "--max-time", "20", url], capture_output=True, text=True)
    return r.stdout.strip()

def main():
    langs = [("Japanisch", "sets_jp.json"), ("Deutsch", "sets_de.json"),
             ("Chinesisch", "sets_cn.json")]
    lines = []      # fehlende-bilder.txt
    spot = []       # console report
    for lang, fn in langs:
        for s in json.load(open(fn, encoding="utf-8")):
            if not s['cards']:
                continue
            code, name = s['code'], s['name']
            # source gaps (never found on the gallery page)
            for n in s.get('missing', []):
                lines.append(f"{lang}\t{code}\t{name}\tNr.{n:03d}\tkein Bild in Galerie/SR-Artikel gefunden")
            # 3 samples: first, middle, last
            cards = s['cards']
            idxs = sorted(set([0, len(cards)//2, len(cards)-1]))
            oks = []
            for i in idxs:
                c = cards[i]
                url = IMGBASE + s['known'][str(c[0])]
                code_http = head(url)
                oks.append(code_http)
                if not code_http.startswith(("2", "3")):
                    lines.append(f"{lang}\t{code}\t{name}\tNr.{c[0]:03d} ({c[1]})\tHTTP {code_http}: {url}")
                time.sleep(0.25)
            spot.append(f"{lang:11s} {code:8s} samples={oks} missing_src={len(s.get('missing',[]))}")
    with open(os.path.join(REPO, "fehlende-bilder.txt"), "w", encoding="utf-8") as f:
        f.write("# Fehlende / nicht erreichbare Kartenbilder\n")
        f.write("# Sprache \t Set \t Set-Name \t Karte \t Grund\n")
        if not lines:
            f.write("# (keine) — alle Stichproben erreichbar, keine Quell-Luecken\n")
        for l in lines:
            f.write(l + "\n")
    print("\n".join(spot))
    print("\nfehlende-bilder.txt: %d Eintraege" % len(lines))

if __name__ == "__main__":
    main()
