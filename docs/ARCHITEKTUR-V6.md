# Architekturprüfung „Kartenfinder V6"

> **Status:** Planungsdokument (Aufgabe 2). Enthält **keine** Code-Änderungen.
> Bewertet jede geplante Funktion auf technische Umsetzbarkeit, nötige
> APIs/Bibliotheken, Risiken, Alternativen und eine empfohlene
> Entwicklungsreihenfolge (MVP zuerst).

---

## 0. Wichtiger Hinweis zum Anforderungsdokument

Im Auftrag war an der Stelle des V6-Anforderungsdokuments nur der Platzhalter
`[HIER DAS V6-ANFORDERUNGSDOKUMENT EINFÜGEN]` enthalten – der eigentliche Text
wurde **nicht mitgeliefert**. Diese Prüfung bewertet daher die Funktionen, die
im Auftrag unter „Berücksichtige dabei zwingend" **konkret benannt** sind:

1. Preisermittlung (Cardmarket-API / Scraping / manuelle Preisspalte)
2. eBay-Anbindung (File-Exchange-CSV vs. Sell API mit OAuth/Backend)
3. Live-Scanner (Browser-Kamera + OCR, z. B. tesseract.js)
4. Mehrbenutzerfähigkeit (nur als Datenmodell-Vorbereitung)
5. Architektur (Standalone-Tools vs. größere Plattform)

Sobald das vollständige V6-Dokument vorliegt, kann dieses Kapitelraster um
weitere Funktionen ergänzt werden. Fehlende Detailanforderungen sind unten je
Funktion als **offene Frage** markiert.

---

## 1. Harte Rahmenbedingungen (gelten für alle Bewertungen)

| Bedingung | Konsequenz für die Architektur |
|-----------|--------------------------------|
| **Kein Server, kein Build, keine Installation** (Schul-Laptop) | Alles läuft als statische HTML-Datei im Browser; Bibliotheken nur per CDN. Kein npm, kein Bundler, kein Node zur Laufzeit. |
| **Start teils per `file://`** (Datei doppelklicken) | Wichtige Browser-APIs sind im `file://`-Kontext **gesperrt** (kein „secure context"): u. a. **Kamera** (`getUserMedia`), Service Worker/PWA, teils Clipboard. → Für alles Kamera-/Offline-App-artige ist **Hosting über HTTPS** nötig (kein Backend, aber Hosting). |
| **Bilder von pokezentrum.de** (Nutzung erlaubt) | Bilder liefern i. d. R. **keine CORS-Header** → `<img>`-Anzeige ok, aber Canvas wird „tainted" (kein PNG-Export). Betrifft schon heute den Titelbild-Generator. |
| **Cardmarket-API stark eingeschränkt**, Scraping unzuverlässig | Automatische Preisermittlung ist **nicht** verlässlich machbar. Manuelle Preisspalte bleibt Basis-Workflow. |

**Zentrale Unterscheidung, die sich durch das ganze Dokument zieht:**

- **„Rein im Browser"** = statische Datei, ggf. per HTTPS gehostet, kein
  eigener Serverprozess. ✅ Passt zur Rahmenbedingung.
- **„Braucht Backend"** = eigener Serverendpunkt für Secrets, OAuth-Redirects,
  Token-Speicherung oder serverseitiges Laden. ⚠️ Widerspricht der
  Grund­bedingung und muss explizit als Zusatz-Infrastruktur begründet werden.

---

## 2. Bewertung je Funktion

### F1 — Preisermittlung

**Ziel:** Verkaufspreise je Karte möglichst automatisch ermitteln.

**Machbarkeit:** ❌ automatisch unzuverlässig · ✅ halbautomatisch (Deep-Links) · ✅ manuell (heute)

| Weg | Bewertung |
|-----|-----------|
| **Cardmarket-API** | OAuth-1.0a; **neue App-Zugänge werden praktisch kaum vergeben** (dedizierter Zugang nur für bestimmte Konten/Widget-Entitlements). Selbst mit Zugang: Preisguide-Abruf ist an kommerzielle Bedingungen geknüpft. App-Secret **kann nicht** sicher in einer statischen Seite liegen → bräuchte Backend. **Nicht empfohlen.** |
| **Cardmarket/eBay scrapen** | Gegen ToS, Cloudflare-geschützt, im Browser wegen CORS ohnehin blockiert; serverseitig unzuverlässig (bestätigt). **Nicht empfohlen.** |
| **eBay-Sold-/Marketplace-Insights-API** | Liefert echte Verkaufspreise, aber Zugang restriktiv (Marketplace Insights nur auf Antrag) und braucht **OAuth-Token serverseitig** → Backend. |
| **Manuelle Preisspalte** (heute in `ebay-export.html`/`erfassung.html`) | ✅ Zuverlässig, null Infrastruktur, volle Kontrolle. **Basis-Workflow beibehalten.** |
| **Preis-Helfer per Deep-Link** (neu, empfohlen) | Pro Karte ein Button, der die **Cardmarket-/eBay-Suchseite** in neuem Tab öffnet (nur eine URL, keine API). Nutzer liest den Preis ab und tippt ihn in die Preisspalte. Rein im Browser, ToS-konform, robust. |

**Nötige APIs/Bibliotheken:** keine (Deep-Links) bzw. Cardmarket-/eBay-API +
Backend (nicht empfohlen).

**Risiken:** API-Zugang, ToS, Wartungsaufwand für Scraper (hoch, brüchig).

**Empfehlung:** Manuelle Preisspalte als Kern. Als Komfort-Ausbau den
**Deep-Link-Preishelfer**. Vollautomatik nur, falls später ein Backend
(Abschnitt 4) ohnehin existiert – dann eBay-API über einen Worker cachen.

> **Offene Frage:** Soll der Preis pro Karte oder pro Sammel-/Variantenangebot
> gepflegt werden? Betrifft, ob der Preishelfer auf Einzelkarten- oder
> Set-Ebene verlinkt.

---

### F2 — eBay-Anbindung

**Ziel:** Angebote bei eBay einstellen.

**Machbarkeit:** ✅ CSV-Weg (heute) · ⚠️ API-Weg (braucht Backend)

| Weg | Bewertung |
|-----|-----------|
| **File-Exchange-CSV** (heute, `ebay-export.html`) | ✅ Kein Backend, kein OAuth. Erzeugt fertige Upload-Dateien (Einzel-Entwürfe + Varianten). Nutzer lädt sie im eBay-Verkäuferportal hoch. **Empfohlener Standard.** |
| **eBay Sell API** (Inventory/Listing, Fulfillment) | Vollautomatisch (anlegen/ändern/beenden), aber: **OAuth-2-Authorization-Code-Flow** mit Redirect-URI und **Refresh-Token-Speicherung**. Client-Secret und Refresh-Token dürfen **nicht** in einer statischen Seite liegen; der Redirect braucht einen **Server-Endpunkt**. → **Backend zwingend.** |

**Nötige Infrastruktur für den API-Weg (falls je gewünscht):**
- Ein kleiner Endpunkt für den OAuth-Token-Tausch + sichere Token-Ablage.
- Minimal: **Cloudflare Workers** (kostenloses Kontingent) + **Workers KV**
  für Refresh-Tokens, oder ein **günstiger VPS** (~3–5 €/Monat). Kein
  Dauerbetrieb nötig, nur bei Aktionen.

**Risiken:** eBay-API-Reviews/Compliance, Token-Ablauf, Wartung; deutlich mehr
Aufwand als CSV.

**Empfehlung:** **Beim CSV-Weg bleiben.** Sell API erst bei hohem
Listing-Volumen erwägen, dann über einen Cloudflare Worker. Der CSV-Weg deckt
den beschriebenen Bedarf (Einzel + Varianten) bereits ab.

---

### F3 — Live-Scanner (Kamera + OCR)

**Ziel:** Karte vor die Kamera halten, Set-Code + Kartennummer (unten links)
automatisch erkennen, Erfassung beschleunigen.

**Machbarkeit:** ⚠️ technisch machbar, aber mit klaren Einschränkungen; die
Zielmarke **1–2 Sekunden/Karte ist optimistisch**.

**Nötige APIs/Bibliotheken:**
- `navigator.mediaDevices.getUserMedia` (Kamera) — **secure context nötig**.
- **tesseract.js** (OCR, WASM, ~2–15 MB, läuft offline nach Erstladen).
- Optional `BarcodeDetector` (nativ, schnell) — **entfällt praktisch**, da
  Pokémon-Karten in der Regel keinen Barcode tragen.

**Kritische Einschränkungen / Risiken:**
1. **`file://` blockiert die Kamera.** `getUserMedia` verlangt einen „secure
   context" (HTTPS oder `localhost`). Vom Schul-Laptop per Doppelklick
   (`file://`) funktioniert die Kamera in den meisten Browsern **nicht**.
   → Der Scanner setzt **Hosting über HTTPS** voraus (Abschnitt 4, Hosting –
   kein Backend). Auf dem Handy ohnehin nur über HTTPS.
2. **Realistische Geschwindigkeit.** tesseract.js ist WASM/Single-Thread. Ein
   voller Frame-OCR dauert je nach Laptop **0,3–2 s+ pro Versuch**; inklusive
   Ausrichten, mehreren Frames bis zu einem stabilen Ergebnis und
   Nutzer-Bestätigung eher **2–5 s/Karte**. Die **1–2-s-Marke ist nur unter
   Idealbedingungen** (gutes Licht, ROI-Crop, fixierte Karte) erreichbar.
3. **Erkennungsqualität.** Das kleine Nummernfeld unten links (z. B.
   `093/187` bzw. `SV8a`) ist klein und kontrastarm. Ohne Vorverarbeitung ist
   die Fehlerrate hoch.

**Bessere Alternativen / Beschleunigung (statt „ganze Karte OCR-en"):**
- **ROI-Crop:** nur die untere linke Ecke ausschneiden, hochskalieren,
  Graustufen + Schwellwert (Binarisierung), dann OCR. Vielfach schneller und
  genauer.
- **Whitelist:** `tessedit_char_whitelist` auf Ziffern, `/` und die im
  Set-Code vorkommenden Zeichen begrenzen.
- **Web Worker:** OCR im Worker, damit die UI nicht blockiert; nur jeden
  n-ten Frame prüfen (Throttling).
- **Mensch schlägt OCR:** Für jemanden, der die Nummern kennt, ist das
  **manuelle Tippen** (heutiger `erfassung.html`-Flow) oft **schneller und
  fehlerfreier** als OCR. OCR lohnt v. a. bei unbekannter Massenware.

**Empfehlung:** OCR als **experimentellen „Assistenz-Modus"**, nicht als
Primärweg. Primär bleibt die schnelle manuelle Nummerneingabe. Voraussetzung
für jeden Kamera-Modus ist vorheriges HTTPS-Hosting (Abschnitt 4).

> **Offene Frage:** Muss der Scanner **offline** im Klassenzimmer laufen? Dann
> tesseract.js-Sprachdaten vorab cachen (Service Worker) — was wiederum HTTPS
> voraussetzt.

---

### F4 — Bildbeschaffung & Galerie-Abgleich (Bestand ausbauen)

**Ziel:** Bestehende Bild-Auflösung (pokezentrum-Galerien) robuster/breiter.

**Machbarkeit:** ✅ heute schon vorhanden; Ausbau rein im Browser möglich.

**Status heute:** `imgCandidates()` (in `kartenbild-finder-v6.html`,
`erfassung.html` **und** `ebay-export.html` dupliziert) probiert Kandidaten-URLs
durch; Fallback-Loader nimmt die erste ladende URL.

**Risiken/Einschränkungen:**
- **CORS/Tainted Canvas:** Für den Titelbild-Export (F über Canvas) liefern die
  Bilder keine CORS-Header → PNG-Export kann scheitern. Heute mit Hinweis +
  Screenshot-Fallback abgefangen. Echte Lösung nur mit gespiegelten Bildern
  auf einem Host mit CORS (→ Hosting/Backend) oder Einbettung als Daten-URI.
- **Rate-Modus (SV8a)** erzeugt viele Kandidaten – langsam bei Massenanzeige.

**Bessere Alternative (Architektur, empfohlen):** Die **dreifach duplizierte**
Bildlogik in ein **gemeinsames `shared.js`** auslegen (siehe F6). Kein Build,
nur ein zusätzliches `<script src>`.

---

### F5 — Mehrbenutzerfähigkeit (nur Datenmodell-Vorbereitung)

**Ziel:** Perspektivisch mehrere Nutzer/Geräte – **jetzt nur vorbereiten**,
nicht umsetzen.

**Machbarkeit heute:** Daten liegen in **localStorage** (ein Gerät, ein Nutzer).
Echte Mehrbenutzer-Synchronisation braucht eine zentrale Datenbank mit Auth →
**Cloud-Backend** (kein selbst betriebener Server nötig, aber ein Dienst).

**Empfohlene Vorbereitung im Datenmodell (ohne Funktionsänderung):**
- **Stabile IDs je Eintrag** (in `erfassung.html` bereits vorhanden) beibehalten
  und auch in Exporten mitführen.
- Optionales Feld **`owner`/`userId`** (vorerst leer/`"local"`) je Eintrag
  vorsehen, damit spätere Zeilen einem Nutzer zuordenbar sind.
- **`updatedAt`/`version`** je Eintrag ergänzen → ermöglicht später
  Konfliktauflösung („last write wins" oder Merge).
- **JSON-Backup als Sync-Einheit** verstehen: schon heute Export/Import; ein
  klar versioniertes Schema (`app`, `version`, `entries[]`) macht eine spätere
  Migration mechanisch.
- Keine geräte-lokalen Annahmen fest verdrahten (z. B. Zeitzonen, lokale
  Zähler).

**Minimal-Infrastruktur, falls später echt gewünscht:**
- **Supabase** (Postgres + Auth + Row-Level-Security) oder **Firebase** –
  beide mit **reinem Browser-SDK per CDN**, kostenloser Tarif, **kein eigener
  Serverprozess**. Das ist der pragmatische Pfad für echte Mehrbenutzer­sync.

**Risiken:** Auth/Datenschutz (Schulkontext!), DSGVO bei personenbezogenen
Daten. Für eine reine Karten-Bestandsliste überschaubar, aber vor einem echten
Multi-User-Schritt zu klären.

**Empfehlung:** Nur die **Datenmodell-Felder** (IDs, `owner`, `updatedAt`,
`version`) einführen. Keinen Sync-Code jetzt.

---

### F6 — Architektur: Standalone-Tools vs. Plattform

**Ziel:** Bewerten, ob die bestehende Struktur (kleine Standalone-HTML-Tools +
gemeinsame `sets-data.js`) tragfähig bleibt.

**Bewertung:** ✅ **Struktur beibehalten.** Sie erfüllt exakt die
Rahmenbedingungen (kein Build, robust auf dem Schul-Laptop, jedes Tool einzeln
per Doppelklick lauffähig) und ist erweiterbar.

**Einziger klarer Architektur-Gewinn ohne Build:**
- Gemeinsame Logik (**Bild-Auflösung `imgCandidates`/`pad`/`findCard`,
  CSV-Helfer, Preis-Parsing, Toast/Download**) ist derzeit über
  `kartenbild-finder-v6.html`, `erfassung.html` und `ebay-export.html`
  **kopiert**. Auslagern in ein **`shared.js`** (zusätzlich zu `sets-data.js`,
  ebenfalls per `<script src>`): weniger Duplikate, eine Stelle für Bugfixes,
  **kein Build-Schritt**.

**Wann Migration zu „mehr Plattform" lohnt (und wann nicht):**
- **Nicht** wegen Optik/Struktur allein – kein Mehrwert, verletzt „kein Build".
- **Erst** wenn geteilter Zustand über Tools hinweg oder npm-Bibliotheken
  nötig werden. Selbst dann ist ein **build-freier ES-Module-Ansatz**
  (`<script type="module">` + optional Import Maps) vorzuziehen, um die
  „keine-Installation"-Bedingung zu wahren.
- Ein PWA-Wrapper (Offline-Fähigkeit, „App"-Icon, Kamera) ist sinnvoll, **setzt
  aber HTTPS-Hosting voraus** und ändert die Grundstruktur nicht.

**Empfehlung:** Standalone-Tools + `sets-data.js` bleiben. Ein `shared.js`
einführen. Kein SPA/Framework, kein Bundler.

---

## 3. Backend-/Infrastruktur-Bedarf im Überblick

| Funktion | Rein im Browser? | Braucht Backend/Hosting? | Minimal-Infrastruktur |
|----------|:----------------:|--------------------------|-----------------------|
| eBay-CSV-Export (heute) | ✅ | — | — |
| Manuelle Preise (heute) | ✅ | — | — |
| Preis-Helfer (Deep-Links) | ✅ | — | — |
| Titelbild-PNG-Export | ⚠️ (CORS) | für sauberen Export: Bild-Host mit CORS | statischer Host mit CORS / Bild-Proxy |
| Live-Scanner (Kamera+OCR) | ⚠️ | **HTTPS-Hosting** (kein Backend) | GitHub Pages / Netlify (gratis) |
| Cardmarket-/eBay-Preis-API | ❌ | **Backend** (Secrets/OAuth) | Cloudflare Worker (gratis) / VPS 3–5 €/M |
| eBay Sell API (Vollautomatik) | ❌ | **Backend** (OAuth-Redirect, Token) | Cloudflare Worker + KV / VPS |
| Mehrbenutzer-Sync | ❌ | **Cloud-DB + Auth** | Supabase / Firebase (Browser-SDK, gratis-Tarif) |

**Kernaussage:** Alles, was der Auftrag heute verlangt, geht **rein im
Browser**. Zusätzliche Infrastruktur ist nur für **Kamera (HTTPS-Hosting,
kein Backend)** sowie für die **optionalen** Ausbaustufen (Preis-API,
Sell-API, Multi-User) nötig – und dann jeweils mit **serverlosen Gratis-
Diensten** (Cloudflare Workers, Supabase) statt eines eigenen Servers.

---

## 4. Empfohlene Entwicklungsreihenfolge (MVP zuerst)

**Phase 0 — erledigt:** eBay-Export-Tool (`ebay-export.html`) + manuelle
Preisspalte. Deckt den Kern-Verkaufs-Workflow bereits ab.

**Phase 1 — `shared.js` (klein, hoher Nutzen, kein Risiko):**
Duplizierte Bild-/CSV-/Preis-Logik in eine gemeinsame Datei auslagern. Reine
Wartbarkeit, keine Verhaltensänderung, kein Build.

**Phase 2 — Preis-Helfer (rein im Browser):**
Pro Karte ein Button „Preis nachschlagen" → öffnet Cardmarket-/eBay-Suche im
neuen Tab. Beschleunigt das manuelle Pflegen der Preisspalte, ToS-konform.

**Phase 3 — HTTPS-Hosting (GitHub Pages/Netlify, gratis):**
Voraussetzung für Kamera, PWA/Offline und Handy-Nutzung. Kein Backend. Danach
laufen die Tools weiterhin auch per `file://`, aber Kamera-Features nur
gehostet.

**Phase 4 — OCR-Assistenz-Scanner (experimentell, benötigt Phase 3):**
tesseract.js mit ROI-Crop + Whitelist + Worker. Als **Zusatz** zur manuellen
Eingabe evaluieren, mit ehrlicher Messung der Karten/Minute.

**Phase 5 — optionale Backend-Ausbaustufen (nur bei echtem Bedarf):**
a) eBay-/Preis-Lookups über einen Cloudflare Worker (Token serverseitig).
b) Mehrbenutzer-Sync über Supabase (Datenmodell aus F5 ist dann vorbereitet).
c) eBay Sell API (Vollautomatik) – nur bei hohem Volumen.

---

## 5. Zusammenfassung / Empfehlung

- **Bestehende Architektur beibehalten** (Standalone-Tools + `sets-data.js`);
  einziger sinnvoller Umbau ohne Build ist ein gemeinsames **`shared.js`**.
- **Preisermittlung** bleibt **manuell** (Basis) + optionaler **Deep-Link-
  Helfer**; automatische Preis-APIs sind unrealistisch/Backend-pflichtig.
- **eBay** über den **CSV-Weg** (erledigt); Sell API nur mit Backend und nur
  bei hohem Volumen.
- **Live-Scanner** ist machbar, aber **HTTPS-Hosting Voraussetzung** und die
  **1–2-s/Karte-Zielmarke unrealistisch**; als Assistenz, nicht als Primärweg.
- **Mehrbenutzer** jetzt nur als **Datenmodell-Vorbereitung** (IDs, `owner`,
  `updatedAt`, `version`); echter Sync später über Supabase/Firebase.
- Zusätzliche Infrastruktur, wo nötig, konsequent **serverlos/gratis**
  (GitHub Pages/Netlify, Cloudflare Workers, Supabase) – **kein eigener
  Server**.

> Dieses Dokument bewertet die im Auftrag benannten Funktionen. Für die im
> V6-Anforderungsdokument evtl. zusätzlich beschriebenen Funktionen bitte den
> Text nachreichen – das Kapitelraster (Machbarkeit · APIs · Risiken ·
> Alternativen · Reihenfolge) lässt sich 1:1 fortführen.
