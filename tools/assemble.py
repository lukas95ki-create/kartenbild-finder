#!/usr/bin/env python3
"""Turn extracted set JSON into JS SETS entries + write links/ files + report."""
import os
import json, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMGBASE = "https://pokezentrum.de/wp-content/uploads/"

def js_set(s):
    known = {int(k): v for k, v in s['known'].items()}
    known_js = "{" + ",".join(f'{k}:{json.dumps(known[k], ensure_ascii=False)}'
                              for k in sorted(known)) + "}"
    cards_js = "[" + ",".join(
        "[" + ",".join(json.dumps(x, ensure_ascii=False) for x in c) + "]"
        for c in s['cards']) + "]"
    return ("{code:%s,name:%s,lang:%s,total:%d,page:%s,\n  known:%s,\n  cards:%s}" % (
        json.dumps(s['code'], ensure_ascii=False),
        json.dumps(s['name'], ensure_ascii=False),
        json.dumps(s['lang'], ensure_ascii=False),
        s['total'],
        json.dumps(s['page'], ensure_ascii=False),
        known_js, cards_js))

def main():
    langs = [("Japanisch", "sets_jp.json"), ("Deutsch", "sets_de.json"),
             ("Chinesisch", "sets_cn.json")]
    all_sets = []
    entries = []
    os.makedirs(os.path.join(REPO, "links"), exist_ok=True)
    report = []
    for lang, fn in langs:
        data = json.load(open(fn, encoding='utf-8'))
        for s in data:
            if not s['cards']:
                report.append((lang, s['code'], 0, 0, "SKIP empty"))
                continue
            all_sets.append(s)
            entries.append(js_set(s))
            # write links file
            lp = os.path.join(REPO, "links", f"{lang}-{s['code']}.txt")
            with open(lp, "w", encoding="utf-8") as f:
                for c in s['cards']:
                    f.write(IMGBASE + s['known'][str(c[0])] + "\n")
            n_secret = sum(1 for c in s['cards'] if c[3] in ('AR','SAR','SR','UR'))
            report.append((lang, s['code'], len(s['cards']), n_secret,
                           f"missing {len(s.get('missing',[]))}"))
    js = ",\n".join(entries)
    open("newsets.js.txt", "w", encoding="utf-8").write(js)
    print("sets:", len(all_sets), "-> newsets.js.txt")
    for r in report:
        print(f"  {r[0]:11s} {r[1]:8s} cards={r[2]:4d} secret={r[3]:3d} {r[4]}")

if __name__ == "__main__":
    main()
