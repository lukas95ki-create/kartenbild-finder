/* =====================================================================
   Automatisierte Tests für die beiden eBay-CSV-Exporte in
   kartenbild-finder-v6.html – Export A (Entwurfs-Vorlage
   "eBay-draft-listings-template_DE") und Export B (Kategorie-Vorlage
   fx_category_template_EBAY_DE, Kategorie 183454). Die Kopfzeilen
   werden zusätzlich gegen die Original-Vorlagendateien in templates/
   abgeglichen.

   Ausführen (im Repo-Hauptverzeichnis):  node --test
   (benötigt nur Node ≥ 18, keine Abhängigkeiten)

   Die CSV-Logik liegt DOM-frei zwischen den Markern
   @EBAY_DRAFT_CSV / @EBAY_EXPORT_RULES / @EBAY_CATEGORY_CSV in der
   HTML-Datei und wird hier extrahiert und direkt ausgeführt –
   getestet wird also exakt der Code, der auch im Browser läuft.
   ===================================================================== */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../kartenbild-finder-v6.html", import.meta.url), "utf8");
const m = html.match(/\/\* @EBAY_DRAFT_CSV_START \*\/([\s\S]*?)\/\* @EBAY_DRAFT_CSV_END \*\//);
assert.ok(m, "Marker-Block @EBAY_DRAFT_CSV_START/_END in kartenbild-finder-v6.html nicht gefunden");

const { EBAY_DRAFT_INFO_LINES, EBAY_DRAFT_HEADER, csvEsc, priceDot, buildDraftCsv, mergeDraftRecords } =
  new Function(m[1] +
    "; return { EBAY_DRAFT_INFO_LINES, EBAY_DRAFT_HEADER, csvEsc, priceDot, buildDraftCsv, mergeDraftRecords };")();

const mRules = html.match(/\/\* @EBAY_EXPORT_RULES_START \*\/([\s\S]*?)\/\* @EBAY_EXPORT_RULES_END \*\//);
assert.ok(mRules, "Marker-Block @EBAY_EXPORT_RULES_START/_END nicht gefunden");
const { exportScope, selectExportRows, missingVariantSettings } =
  new Function(mRules[1] +
    "; return { exportScope, selectExportRows, missingVariantSettings };")();

/* Kategorie-Block braucht csvEsc aus dem Draft-Block → beide konkateniert. */
const mCat = html.match(/\/\* @EBAY_CATEGORY_CSV_START \*\/([\s\S]*?)\/\* @EBAY_CATEGORY_CSV_END \*\//);
assert.ok(mCat, "Marker-Block @EBAY_CATEGORY_CSV_START/_END nicht gefunden");
const { EBAY_CATEGORY_INFO_LINE, EBAY_CATEGORY_HEADER, COLS_B, makeRowB, buildCategoryCsv } =
  new Function(m[1] + ";" + mCat[1] +
    "; return { EBAY_CATEGORY_INFO_LINE, EBAY_CATEGORY_HEADER, COLS_B, makeRowB, buildCategoryCsv };")();

/* ---------- Offizielle Vorlagendateien aus templates/ ---------- */
import { readdirSync } from "node:fs";
const tplDir = new URL("../templates/", import.meta.url);
function readTemplate(prefix) {
  const name = readdirSync(tplDir).find(f => f.startsWith(prefix) && f.endsWith(".csv"));
  assert.ok(name, `Vorlagendatei ${prefix}*.csv fehlt in templates/`);
  return readFileSync(new URL(name, tplDir), "utf8");
}
const draftTpl    = readTemplate("eBay-draft-listing-template");
const categoryTpl = readTemplate("eBay-category-listing-template");
/* Vorlagen zeilenweise – die Kategorie-Vorlage nutzt CR-only-Zeilenenden. */
const tplLines = t => t.replace(/^\uFEFF/, "").split(/\r\n|\r|\n/);

/* Eine CSV-Zeile in Felder zerlegen (Semikolon, "…"-Quoting, ""-Escape). */
function splitCsvLine(line) {
  const out = []; let cur = "", inQ = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQ) {
      if (ch === '"') { if (line[i + 1] === '"') { cur += '"'; i++; } else inQ = false; }
      else cur += ch;
    }
    else if (ch === '"') inQ = true;
    else if (ch === ";") { out.push(cur); cur = ""; }
    else cur += ch;
  }
  out.push(cur);
  return out;
}

const BOM = "﻿";
const REC = {
  sku: "SV8A-005",
  categoryId: "183454",
  title: "Pokemon Testkarte 005 SV8a Japanisch",
  price: 1.5,
  qty: 2,
  photoUrl: "https://example.com/bild.jpg",
  conditionId: "",
  description: "Einfache Beschreibung ohne Sonderzeichen"
};
function csvFor(over = {}) { return buildDraftCsv([{ ...REC, ...over }]); }
function linesFor(over = {}) { return csvFor(over).slice(BOM.length).split("\r\n"); }

test("CSV beginnt mit UTF-8 BOM (genau einem)", () => {
  const csv = csvFor();
  assert.ok(csv.startsWith(BOM), "BOM fehlt am Dateianfang");
  assert.ok(!csv.slice(1).includes(BOM), "BOM darf nur einmal vorkommen");
});

test("Zeile 1 ist exakt die eBay-Vorlagen-Kennung", () => {
  assert.equal(linesFor()[0],
    "#INFO;Version=0.0.2;Template= eBay-draft-listings-template_DE;;;;;;;");
});

test("Zeilen 2–4 sind exakt die restlichen #INFO-Zeilen der Vorlage", () => {
  const lines = linesFor();
  assert.equal(lines[1],
    "#INFO Action und Category ID sind erforderliche Felder. 1) Stellen Sie Action auf Draft ein. 2) Die Kategorie-ID für Ihre Angebote finden Sie hier: https://pages.ebay.com/sellerinformation/news/categorychanges.html;;;;;;;;;");
  assert.equal(lines[2],
    "#INFO Nachdem Sie Ihren Entwurf erfolgreich im Berichte-Tab Ihres Verkäufer-Cockpit Pro heruntergeladen haben; können Sie die Entwürfe hier zu aktiven Angeboten vervollständigen: https://www.ebay.de/sh/lst/drafts;;;;;;;;;");
  assert.equal(lines[3], "#INFO;;;;;;;;;;");
  assert.deepEqual(EBAY_DRAFT_INFO_LINES, lines.slice(0, 4),
    "Konstante EBAY_DRAFT_INFO_LINES weicht von der Ausgabe ab");
});

test("Zeile 5 ist exakt die Kopfzeile der Vorlage", () => {
  assert.equal(linesFor()[4],
    "Action(SiteID=Germany|Country=DE|Currency=EUR|Version=1193|CC=UTF-8);Custom label (SKU);Category ID;Title;UPC;Price;Quantity;Item photo URL;Condition ID;Description;Format");
  assert.equal(EBAY_DRAFT_HEADER, linesFor()[4]);
});

test("Zeilenenden sind durchgehend CRLF, Datei endet mit CRLF", () => {
  const csv = csvFor();
  const rest = csv.slice(BOM.length).replace(/\r\n/g, "");
  assert.ok(!rest.includes("\n"), "einzelnes \\n gefunden");
  assert.ok(!rest.includes("\r"), "einzelnes \\r gefunden");
  assert.ok(csv.endsWith("\r\n"), "Datei endet nicht mit CRLF");
});

test("Datensatz ab Zeile 6: Action=Draft, Category ID und Preis mit Punkt", () => {
  const fields = linesFor()[5].split(";");
  assert.equal(fields[0], "Draft");                       // Action
  assert.equal(fields[1], "SV8A-005");                    // Custom label (SKU)
  assert.equal(fields[2], "183454");                      // Category ID pro Zeile
  assert.equal(fields[3], REC.title);                     // Title
  assert.equal(fields[4], "");                            // UPC leer
  assert.equal(fields[5], "1.50");                        // Preis mit Punkt
  assert.equal(fields[6], "2");                           // Quantity
  assert.equal(fields[7], REC.photoUrl);                  // Item photo URL
  assert.equal(fields[10], "FixedPrice");                 // Format
});

test("Category ID ist in JEDER Datenzeile befüllt", () => {
  const csv = buildDraftCsv([REC, { ...REC, sku: "SV8A-006" }, { ...REC, sku: "SV8A-007" }]);
  const dataLines = csv.slice(BOM.length).split("\r\n").slice(5).filter(l => l !== "");
  assert.equal(dataLines.length, 3);
  dataLines.forEach(l => assert.equal(l.split(";")[2], "183454"));
});

test("Semikolon-Escaping: Feld mit ; wird in doppelte Anführungszeichen gesetzt", () => {
  const line = linesFor({ title: "Karte; mit Semikolon" })[5];
  assert.ok(line.includes('"Karte; mit Semikolon"'), line);
});

test("Anführungszeichen im Feld werden verdoppelt und das Feld quotiert", () => {
  const line = linesFor({ title: 'Karte "Rar"; Sonderdruck' })[5];
  assert.ok(line.includes('"Karte ""Rar""; Sonderdruck"'), line);
});

test("Zeilenumbruch im Feld wird quotiert (keine zusätzliche CSV-Zeile)", () => {
  const csv = csvFor({ description: "Zeile 1\nZeile 2" });
  const body = csv.slice(BOM.length);
  assert.ok(body.includes('"Zeile 1\nZeile 2"'), "Feld mit Umbruch nicht quotiert");
  // Nach Entfernen der quotierten Felder darf kein \n ohne \r übrig bleiben:
  const unquoted = body.replace(/"(?:[^"]|"")*"/g, "");
  assert.ok(!unquoted.replace(/\r\n/g, "").includes("\n"));
});

test("HTML-Beschreibung mit Inline-CSS (enthält ;) wird quotiert", () => {
  const line = linesFor({ description: "<div style='font-size:15px;color:#222'>Text</div>" })[5];
  assert.ok(line.includes("\"<div style='font-size:15px;color:#222'>Text</div>\""), line);
});

test("csvEsc: Grundfälle", () => {
  assert.equal(csvEsc("einfach"), "einfach");
  assert.equal(csvEsc(null), "");
  assert.equal(csvEsc("a;b"), '"a;b"');
  assert.equal(csvEsc('a"b'), '"a""b"');
  assert.equal(csvEsc("a\r\nb"), '"a\r\nb"');
});

test("priceDot: Punkt als Dezimaltrenner, zwei Nachkommastellen", () => {
  assert.equal(priceDot(1.5), "1.50");
  assert.equal(priceDot(2), "2.00");
  assert.equal(priceDot(0.99), "0.99");
  assert.equal(priceDot(null), "");
});

test("Duplikate (gleiche SKU + Titel) werden zu EINER Zeile mit summierter Quantity", () => {
  const csv = buildDraftCsv([
    { ...REC, qty: 1 },
    { ...REC, qty: 2 },
    { ...REC, sku: "SV8A-006", title: "Pokemon Andere Karte 006 SV8a Japanisch", qty: 1 }
  ]);
  const dataLines = csv.slice(BOM.length).split("\r\n").slice(5).filter(l => l !== "");
  assert.equal(dataLines.length, 2, "Duplikat wurde nicht zusammengefasst");
  assert.equal(dataLines[0].split(";")[6], "3", "Quantity nicht summiert (1+2)");
});

test("Ball-Varianten (gleiche SKU, anderer Titel) bleiben getrennte Zeilen", () => {
  const merged = mergeDraftRecords([
    { ...REC, qty: 1 },
    { ...REC, qty: 1, title: REC.title + " Master Ball" }
  ]);
  assert.equal(merged.length, 2);
});

test("Export-Modus 'singles': ALLE Karten in die Entwurfs-CSV, Export B leer (nur eine Datei)", () => {
  const rows = [
    { mode: "single",  price: 1.5, id: 1 },
    { mode: "variant", price: 2.0, id: 2 },
    { mode: "variant", price: null, id: 3 }   // ohne Preis → ausgeschlossen
  ];
  const singles = selectExportRows(rows, "singles", "single");
  assert.deepEqual(singles.map(o => o.id), [1, 2], "nicht alle bepreisten Karten im Draft-Export");
  assert.equal(selectExportRows(rows, "singles", "variant").length, 0,
    "Export B müsste im Modus 'singles' leer sein (keine zweite Datei)");
});

test("Export-Modus 'singles' + Duplikate: genau eine CSV mit einer Zeile pro Karte", () => {
  const rows = [
    { mode: "variant", price: 1.5, sku: "SV8A-005", qty: 1 },
    { mode: "single",  price: 1.5, sku: "SV8A-005", qty: 2 },  // Duplikat
    { mode: "variant", price: 2.0, sku: "SV8A-006", qty: 1 }
  ];
  const selected = selectExportRows(rows, "singles", "single");
  assert.equal(selected.length, 3);
  const csv = buildDraftCsv(selected.map(o => ({
    ...REC, sku: o.sku, title: "Pokemon Karte " + o.sku, price: o.price, qty: o.qty
  })));
  const dataLines = csv.slice(BOM.length).split("\r\n").slice(5).filter(l => l !== "");
  assert.equal(dataLines.length, 2, "erwartet: eine Zeile pro Karte (Duplikat via Quantity)");
  assert.equal(dataLines[0].split(";")[6], "3");
  assert.equal(selectExportRows(rows, "singles", "variant").length, 0,
    "im Modus 'singles' darf keine Varianten-CSV entstehen");
});

test("Export-Modus 'auto' teilt nach o.mode auf, 'variants' schickt alles in Export B", () => {
  const rows = [
    { mode: "single",  price: 1.5, id: 1 },
    { mode: "variant", price: 2.0, id: 2 }
  ];
  assert.deepEqual(selectExportRows(rows, "auto", "single").map(o => o.id), [1]);
  assert.deepEqual(selectExportRows(rows, "auto", "variant").map(o => o.id), [2]);
  assert.deepEqual(selectExportRows(rows, "variants", "variant").map(o => o.id), [1, 2]);
  assert.equal(selectExportRows(rows, "variants", "single").length, 0);
  // exportScope zählt auch preislose Zeilen (für die Übersprungen-Meldung):
  assert.equal(exportScope([{ mode: "single", price: null }], "singles", "single").length, 1);
});

test("Export B wird bei leeren Pflichtfeldern blockiert (fehlende Felder benannt)", () => {
  assert.deepEqual(
    missingVariantSettings({ location: "", dispatch: "", shipService: "", shipCost: null }),
    ["Standort", "Versandart", "Versandkosten", "Bearbeitungszeit"]);
  assert.deepEqual(
    missingVariantSettings({ location: "Berlin", dispatch: "2", shipService: "DE_DeutschePostBrief", shipCost: null }),
    ["Versandkosten"]);
  assert.deepEqual(
    missingVariantSettings({ location: "Berlin", dispatch: "2", shipService: "DE_DeutschePostBrief", shipCost: 1.8 }),
    []);
  // Blockade ist in doExportB verdrahtet: keine Datei, sichtbare Meldung
  assert.ok(/doExportB\(\)\{[\s\S]*?missingVariantSettings\([\s\S]*?if \(miss\.length\)\{[\s\S]*?showExportBError\([\s\S]*?return;/.test(html),
    "doExportB blockiert nicht sichtbar bei fehlenden Pflichtfeldern");
});

test("UI: Warnhinweis 'sofort live' und Standard-Modus 'Alle als Einzelentwürfe' vorhanden", () => {
  const flat = html.replace(/\s+/g, " ");
  assert.ok(flat.includes("Variationsangebote gehen beim Hochladen <b>sofort live</b> – Entwürfe sind hier nicht möglich"),
    "Warnhinweis zum Sofort-live-Verhalten fehlt");
  assert.ok(flat.includes('<option value="singles">Alle als Einzelentwürfe</option>'),
    "Export-Modus-Option 'Alle als Einzelentwürfe' fehlt");
  assert.ok(html.includes('? s.exportMode : "singles"'),
    "Standard-Export-Modus ist nicht 'singles'");
});

test("Varianten-Export nutzt einen ANDEREN Header (Draft-Vorlage kann keine Varianten)", () => {
  assert.notEqual(EBAY_CATEGORY_HEADER, EBAY_DRAFT_HEADER);
  assert.ok(EBAY_CATEGORY_HEADER.startsWith("*Action(SiteID=Germany|Country=DE|Currency=EUR|Version=1193|CC=UTF-8);"));
  assert.ok(html.includes("unterstützt <b>keine Varianten</b>"),
    "UI-Hinweis zum Varianten-Export fehlt");
});

/* =====================================================================
   Abgleich mit den offiziellen Vorlagendateien in templates/
   ===================================================================== */
test("Vorlagendateien: beide beginnen mit UTF-8 BOM", () => {
  assert.ok(draftTpl.startsWith("﻿"), "Draft-Vorlage ohne BOM");
  assert.ok(categoryTpl.startsWith("﻿"), "Kategorie-Vorlage ohne BOM");
});

test("Export A: #INFO-Zeilen und Kopfzeile identisch mit der Draft-Vorlagendatei", () => {
  const tpl = tplLines(draftTpl);
  assert.deepEqual(EBAY_DRAFT_INFO_LINES, tpl.slice(0, 4),
    "#INFO-Zeilen weichen von der Vorlagendatei ab");
  assert.equal(EBAY_DRAFT_HEADER, tpl[4],
    "Kopfzeile weicht von der Vorlagendatei ab");
  // und die ERZEUGTE Datei beginnt exakt mit diesen 5 Zeilen:
  const out = linesFor();
  assert.deepEqual(out.slice(0, 5), tpl.slice(0, 5));
});

test("Export B: Info-Zeile und Kopfzeile identisch mit der Kategorie-Vorlagendatei", () => {
  const tpl = tplLines(categoryTpl);
  assert.equal(EBAY_CATEGORY_INFO_LINE, tpl[0],
    "Info-Kennungszeile weicht von der Vorlagendatei ab");
  assert.equal(EBAY_CATEGORY_HEADER, tpl[1],
    "Kopfzeile weicht von der Vorlagendatei ab (Spalten exakt wie im Original)");
  assert.equal(COLS_B.length, tpl[1].split(";").length, "Spaltenanzahl weicht ab");
});

test("Export B: erzeugte CSV – BOM, CRLF, Kopfzeilen aus der Vorlage", () => {
  const P = makeRowB();
  P["*Action(SiteID=Germany|Country=DE|Currency=EUR|Version=1193|CC=UTF-8)"] = "Add";
  P["*Category"] = "183454";
  P["*Title"] = "Pokemon Testset SV8a Japanisch - Einzelkarten zum Aussuchen";
  P["RelationshipDetails"] = "Kartenname=Karte A 005;Karte B 006";
  const C = makeRowB();
  C["*Action(SiteID=Germany|Country=DE|Currency=EUR|Version=1193|CC=UTF-8)"] = "Add";
  C["Relationship"] = "Variation";
  C["RelationshipDetails"] = "Kartenname=Karte A 005";
  C["*StartPrice"] = "1.50";
  C["*Quantity"] = "2";
  const csv = buildCategoryCsv([P, C]);

  assert.ok(csv.startsWith("﻿"), "BOM fehlt");
  assert.ok(!csv.slice(1).includes("﻿"), "BOM mehrfach");
  const rest = csv.slice(1).replace(/\r\n/g, "");
  assert.ok(!rest.includes("\n") && !rest.includes("\r"), "Zeilenenden nicht durchgehend CRLF");
  assert.ok(csv.endsWith("\r\n"), "Datei endet nicht mit CRLF");

  const lines = csv.slice(1).split("\r\n");
  const tpl = tplLines(categoryTpl);
  assert.equal(lines[0], tpl[0], "Zeile 1 (Info) weicht von der Vorlage ab");
  assert.equal(lines[1], tpl[1], "Zeile 2 (Kopfzeile) weicht von der Vorlage ab");
});

test("Export B: jede Zeile hat exakt so viele Spalten wie die Vorlagen-Kopfzeile", () => {
  const P = makeRowB();
  P["*Title"] = "Titel; mit Semikolon";                      // erzwingt Quoting
  P["RelationshipDetails"] = 'Kartenname=Wert "A";Wert B';   // Quotes + Semikolon
  const C = makeRowB();
  C["Relationship"] = "Variation";
  const csv = buildCategoryCsv([P, C]);
  const nCols = tplLines(categoryTpl)[1].split(";").length;
  const lines = csv.slice(1).split("\r\n").filter(l => l !== "");
  assert.equal(lines.length, 4);   // Info + Header + 2 Datenzeilen
  lines.slice(1).forEach((l, i) =>
    assert.equal(splitCsvLine(l).length, nCols, `Zeile ${i + 2} hat falsche Spaltenanzahl`));
});

test("Export A: jede Datenzeile hat exakt so viele Spalten wie die Draft-Kopfzeile", () => {
  const nCols = tplLines(draftTpl)[4].split(";").length;
  const lines = csvFor({ title: "Karte; mit Semikolon" }).slice(1).split("\r\n").filter(l => l !== "");
  assert.equal(splitCsvLine(lines[4]).length, nCols, "Kopfzeile");
  assert.equal(splitCsvLine(lines[5]).length, nCols, "Datenzeile");
});

test("buildCsvB im HTML nutzt buildCategoryCsv (Vorlagen-Kopfzeilen) statt eigener Header", () => {
  assert.ok(/function buildCsvB\(\)\{[\s\S]*?return buildCategoryCsv\(rows\);/.test(html),
    "buildCsvB gibt nicht buildCategoryCsv(rows) zurück");
  assert.ok(!/const HEADER_B\b/.test(html), "alte HEADER_B-Konstante existiert noch");
});
