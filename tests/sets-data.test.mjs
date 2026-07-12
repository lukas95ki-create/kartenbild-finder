/* =====================================================================
   Integritäts-Tests für sets-data.js und die Raritäts-Filter-Logik
   der Kartensuche in kartenbild-finder-v6.html.

   Ausführen (im Repo-Hauptverzeichnis):  node --test
   ===================================================================== */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const ctx = {};
new Function(
  readFileSync(new URL("../sets-data.js", import.meta.url), "utf8") +
  "; this.BASE = BASE; this.SETS = SETS;"
).call(ctx);
const SETS = ctx.SETS;

const html = readFileSync(new URL("../kartenbild-finder-v6.html", import.meta.url), "utf8");
/* Dieselbe Regex wie in der App (Konstante EX_NAME_RE). */
const reMatch = html.match(/const EX_NAME_RE = (\/.*?\/i);/);
assert.ok(reMatch, "EX_NAME_RE nicht in kartenbild-finder-v6.html gefunden");
const EX_NAME_RE = new Function("return " + reMatch[1])();

const RARITY_VOCAB = ["ex", "AR", "SAR", "SR", "UR", "MUR", "ACE", "Gold"];

test("Raritätsfelder enthalten nur bekannte Werte", () => {
  for (const s of SETS)
    for (const c of s.cards)
      if (c[3]) assert.ok(RARITY_VOCAB.includes(c[3]),
        `${s.code} Nr.${c[0]}: unbekannte Rarität "${c[3]}"`);
});

test("Kein Set ist flächendeckend als 'ex' markiert (SV4a/M2a-Bug)", () => {
  for (const s of SETS) {
    const ex = s.cards.filter(c => c[3] === "ex").length;
    assert.ok(ex < s.cards.length * 0.5,
      `${s.code}: ${ex}/${s.cards.length} Karten als ex markiert – pauschale Fehl-Markierung?`);
  }
});

test("Jede 'ex'-Markierung passt zum Kartennamen (…-ex)", () => {
  for (const s of SETS)
    for (const c of s.cards)
      if (c[3] === "ex") assert.ok(EX_NAME_RE.test(c[1]),
        `${s.code} Nr.${c[0]} "${c[1]}" ist als ex markiert, hat aber kein -ex im Namen`);
});

test("EX_NAME_RE: echte ex-Namen matchen, Exeggcute/Exploud nicht", () => {
  for (const name of ["Glurak-ex-SV4a", "Mantidea-ex", "Team-Rockets-Iksbat-ex", "Mega-Zeraora-ex"])
    assert.ok(EX_NAME_RE.test(name), name + " müsste matchen");
  for (const name of ["Owei-Exeggcute", "Kokowei-Exeggutor", "Krawumms-Exploud", "Riffex"])
    assert.ok(!EX_NAME_RE.test(name), name + " dürfte NICHT matchen");
});

test("Secret-Karten (Nr > total) haben immer ein Raritätsfeld (Basis des Common-Filters)", () => {
  for (const s of SETS)
    for (const c of s.cards)
      if (c[0] > s.total) assert.ok(c[3],
        `${s.code} Nr.${c[0]} liegt über total=${s.total}, hat aber kein Raritätsfeld`);
});

test("Filter-Kategorien liefern je Set eine echte Teilmenge (nie alle Karten)", () => {
  const isEx = c => c[3] === "ex" || EX_NAME_RE.test(c[1]);
  for (const s of SETS) {
    const ex = s.cards.filter(isEx).length;
    assert.ok(ex < s.cards.length, `${s.code}: ex-Filter = alle ${s.cards.length} Karten`);
    const common = s.cards.filter(c => !c[3] && !EX_NAME_RE.test(c[1]) && c[0] <= s.total).length;
    assert.ok(common > 0, `${s.code}: Common-Filter leer`);
    /* Common < alle gilt nur, wenn das Set überhaupt Raritätsinfo trägt –
       CBB1C z. B. hat (noch) keine, dort ist Common = alle Karten korrekt. */
    const hasRarityInfo = s.cards.some(c => c[3] || EX_NAME_RE.test(c[1]));
    if (hasRarityInfo)
      assert.ok(common < s.cards.length, `${s.code}: Common-Filter = alle Karten trotz Raritätsdaten`);
  }
});

test("SV10 'The Glory of Team Rocket' ist vollständig hinterlegt", () => {
  const s = SETS.find(x => x.code === "SV10");
  assert.ok(s, "SV10 fehlt");
  assert.equal(s.lang, "Japanisch");
  assert.equal(s.total, 98);
  assert.equal(s.cards.length, 132);
  assert.equal(Object.keys(s.known).length, 132, "jede SV10-Karte braucht einen exakten Dateinamen");
  const r = s.cards.reduce((a, c) => { const k = c[3] || "basis"; a[k] = (a[k] || 0) + 1; return a; }, {});
  assert.deepEqual(r, { basis: 90, ex: 8, AR: 12, SR: 13, SAR: 6, UR: 3 });
  for (const [n, f] of Object.entries(s.known))
    assert.ok(f.includes("SV10"), `SV10 Nr.${n}: Dateiname ohne SV10: ${f}`);
});

test("Basis-Invarianten: Codes eindeutig, Nummern je Set eindeutig, BASE-URL korrekt", () => {
  assert.equal(ctx.BASE, "https://pokezentrum.de/wp-content/uploads/");
  const codes = SETS.map(s => s.code);
  assert.equal(new Set(codes).size, codes.length, "doppelte Set-Codes");
  for (const s of SETS) {
    const nums = s.cards.map(c => c[0]);
    assert.equal(new Set(nums).size, nums.length, `${s.code}: doppelte Kartennummern`);
  }
});
