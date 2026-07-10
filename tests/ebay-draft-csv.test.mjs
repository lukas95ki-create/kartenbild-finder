/* =====================================================================
   Automatisierte Tests für den eBay-Entwurfs-Export (Export A) in
   kartenbild-finder-v6.html.

   Ausführen (im Repo-Hauptverzeichnis):  node --test
   (benötigt nur Node ≥ 18, keine Abhängigkeiten)

   Die CSV-Logik liegt DOM-frei zwischen den Markern
   @EBAY_DRAFT_CSV_START / @EBAY_DRAFT_CSV_END in der HTML-Datei und
   wird hier extrahiert und direkt ausgeführt – getestet wird also
   exakt der Code, der auch im Browser läuft.
   ===================================================================== */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../kartenbild-finder-v6.html", import.meta.url), "utf8");
const m = html.match(/\/\* @EBAY_DRAFT_CSV_START \*\/([\s\S]*?)\/\* @EBAY_DRAFT_CSV_END \*\//);
assert.ok(m, "Marker-Block @EBAY_DRAFT_CSV_START/_END in kartenbild-finder-v6.html nicht gefunden");

const { EBAY_DRAFT_INFO_LINES, EBAY_DRAFT_HEADER, csvEsc, priceDot, buildDraftCsv } =
  new Function(m[1] +
    "; return { EBAY_DRAFT_INFO_LINES, EBAY_DRAFT_HEADER, csvEsc, priceDot, buildDraftCsv };")();

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

test("Varianten-Export nutzt einen ANDEREN Header (Draft-Vorlage kann keine Varianten)", () => {
  // HEADER_B (File Exchange) muss weiterhin existieren und darf nicht mit
  // dem Draft-Header identisch sein; der UI-Hinweis dazu muss vorhanden sein.
  const hb = html.match(/const HEADER_B =\s*\n?\s*"([^"]+)"/);
  assert.ok(hb, "HEADER_B nicht gefunden");
  assert.notEqual(hb[1], EBAY_DRAFT_HEADER);
  assert.ok(hb[1].startsWith("*Action(SiteID=Germany|Country=DE|Currency=EUR|Version=1193|CC=UTF-8);"));
  assert.ok(html.includes("unterstützt <b>keine Varianten</b>"),
    "UI-Hinweis zum Varianten-Export fehlt");
});
