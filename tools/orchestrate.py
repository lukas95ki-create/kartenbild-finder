#!/usr/bin/env python3
"""Download galleries+SR articles, extract exact filenames, emit links files
and a JS SETS array. Config is a list of dicts below (or via --config json)."""
import os, sys, time, json, subprocess, urllib.parse, argparse
import extract as EX

BASE = "https://pokezentrum.de/pokemon-karten-news/"
IMGBASE = "https://pokezentrum.de/wp-content/uploads/"
HTML_DIR = "html"
os.makedirs(HTML_DIR, exist_ok=True)

def fetch(slug, tag, delay=1.0):
    url = BASE + slug + "/"
    path = os.path.join(HTML_DIR, tag + ".html")
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path, True
    time.sleep(delay)
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", "45", url, "-o", path,
                        "-w", "%{http_code}"], capture_output=True, text=True)
    code = r.stdout.strip()
    ok = code.startswith("2") and os.path.exists(path) and os.path.getsize(path) > 1000
    return path, ok

def process(cfg):
    """cfg: dict(code,name,lang,gallery,sr[list],marker,total)"""
    files = []
    gpath, ok = fetch(cfg['gallery'], cfg['code'] + "-gallery")
    if ok:
        files.append(gpath)
    galleries_ok = ok
    for i, sr in enumerate(cfg.get('sr', [])):
        spath, sok = fetch(sr, cfg['code'] + f"-sr{i}")
        if sok:
            files.append(spath)
    if not files:
        return None, {"code": cfg['code'], "error": "no html"}
    r = EX.build(files, cfg.get('total'), cfg['code'], cfg.get('marker'), cfg.get('scheme', 'auto'))
    r['name'] = cfg['name']; r['lang'] = cfg['lang']
    r['page'] = BASE + cfg['gallery'] + "/"
    r['gallery_ok'] = galleries_ok
    return r, {"code": cfg['code'], "total": r['total'], "base": r['n_base'],
               "secret": r['n_secret'], "missing": r['missing'],
               "cards": len(r['cards'])}

def write_links(r, links_dir):
    os.makedirs(links_dir, exist_ok=True)
    fn = os.path.join(links_dir, f"{r['lang']}-{r['code']}.txt")
    with open(fn, "w", encoding="utf-8") as f:
        for c in r['cards']:
            f.write(IMGBASE + r['known'][c[0]] + "\n")
    return fn

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    cfgs = json.load(open(a.config, encoding='utf-8'))
    results = []
    report = []
    for cfg in cfgs:
        r, rep = process(cfg)
        report.append(rep)
        print(json.dumps(rep, ensure_ascii=False))
        if r:
            results.append(r)
            write_links(r, "links_out")
    json.dump(results, open(a.out, "w", encoding="utf-8"), ensure_ascii=False)
    print("WROTE", a.out, "sets=", len(results))
