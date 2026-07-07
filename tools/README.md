# Generatoren für kartenbild-finder-v6.html

Diese Skripte erzeugen die Set-Daten aus den PokeZentrum-Galerien
(exakte Bild-Dateinamen, kein Raten) und bauen sie in die App ein.

Ablauf (aus dem Repo-Wurzelverzeichnis, `cd tools`):

```
python3 orchestrate.py --config config_jp.json --out sets_jp.json   # Japanisch
python3 orchestrate.py --config config_de.json --out sets_de.json   # Deutsch
python3 orchestrate.py --config config_cn.json --out sets_cn.json   # Chinesisch
python3 assemble.py    # schreibt links/*.txt und tools/newsets.js.txt
python3 check.py       # 3 Stichproben je Set, schreibt fehlende-bilder.txt
```

- `orchestrate.py` lädt Galerie + zugehörige „Alle Secret-Rare-Karten"-Artikel
  (1 s Pause pro Abruf) und cached sie unter `tools/html/`.
- `extract.py` zieht die exakten Dateinamen; erkennt Total automatisch,
  taggt Kategorien (ex/AR/SAR/SR/UR) aus dem Dateinamen und behandelt die
  drei Namensschemata der Seite (Bindestrich, Unterstrich, Führungsnummer)
  plus einen `loose`-Modus für die chinesischen Gem Packs.
- Einträge in `newsets.js.txt` werden manuell/als Ersatz in das `SETS`-Array
  der HTML eingesetzt (die 4 ursprünglichen Sets bleiben unverändert).

Neues Set ergänzen: Zeile in die passende `config_*.json` eintragen
(`code`, `name`, `lang`, `gallery`-Slug, optional `sr`, `scheme`, `marker`).
