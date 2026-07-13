/* ============================================================
   shared.js  —  Gemeinsame Bild- und Set-Logik (Modul „Bildverwaltung“)
   Wird von erfassung.html und kartenbild-finder-v6.html geladen
   (nach sets-data.js, das BASE und SETS definiert).

   Bild-Auflösungs-Kaskade (ARCHITEKTUR-V6, Kap. 3):
     1. assets/cards/SETCODE-NNN.jpg   (lokale Bilddatenbank, gleiche Origin)
     2. pokezentrum-URL(s)             (bisherige Logik)
     3. Platzhalter                    (übernehmen die Seiten selbst)

   Alle Funktionen greifen erst beim Aufruf auf SETS/BASE zu, damit die
   Ladereihenfolge unkritisch bleibt.
   ============================================================ */
"use strict";
(function(global){

  function pad(n){ return String(n).padStart(3, "0"); }

  /* Kanonischer Kartencode: SETCODE-NNN (Schema v2, ARCHITEKTUR-V6 Kap. 2) */
  function kartencode(setCode, num){
    return String(setCode || "").toUpperCase() + "-" + pad(parseInt(num, 10) || 0);
  }

  /* Pfad in der lokalen Bilddatenbank (Kaskaden-Stufe 1) */
  function localImgPath(setCode, num){
    return "assets/cards/" + kartencode(setCode, num) + ".jpg";
  }

  function findCardIn(set, n){ return set.cards.find(c => c[0] === n); }

  function setByCodeLang(code, lang){
    return global.SETS.find(s => s.code === code && s.lang === lang);
  }

  /* Set-Suche: case-insensitiv, bevorzugt die gewünschte Sprache;
     sonst erste Fundstelle (langMismatch=true). */
  function findSetByCode(code, lang){
    const c = String(code || "").trim().toLowerCase();
    let s = global.SETS.find(x => x.code.toLowerCase() === c && x.lang === lang);
    if (s) return { set: s, langMismatch: false };
    s = global.SETS.find(x => x.code.toLowerCase() === c);
    return s ? { set: s, langMismatch: true } : null;
  }

  /* Bild-Kandidaten für eine Karte. Leeres Array = Karte nicht hinterlegt
     (die Seiten zeigen dann ihren „nicht hinterlegt“-Hinweis). */
  function imgCandidatesFor(set, n){
    const local = localImgPath(set.code, n);
    if (set.known && set.known[n]) return [local, global.BASE + set.known[n]];
    const e = findCardIn(set, n);
    if (!e) return [];
    const files = [e[1], ...(e[2] || [])];
    // Exakter Modus: Set hat festes Dateinamens-Ende
    if (set.suffix){
      return [local, ...files.map(f => `${global.BASE}${f}-${pad(n)}${set.suffix}`)];
    }
    // Rate-Modus (SV8a): Varianten durchprobieren
    const isEx = /-ex/i.test(e[1]);
    const isTrainer = n >= 137 && set.code === "SV8a";
    let mids, posts;
    if (isEx){ mids = ["-Terakristall","-Terakistall","-Holo","","-Holo-Terakristall"]; posts = ["-RR",""]; }
    else if (isTrainer){ mids = ["-Holo","","-ASS-KLASSE","-Holo-ASS-KLASSE"]; posts = ["","-ACE"]; }
    else { mids = ["-Holo",""]; posts = [""]; }
    const tails = ["-TCG",""];
    const urls = [local];
    for (const f of files) for (const p of posts) for (const m of mids) for (const t of tails)
      urls.push(`${global.BASE}${f}-${pad(n)}-${set.total}${p}-SV8a-Terastal-Festival-ex${m}-Pokemon-Karte-Japan${t}.jpg`);
    return urls;
  }

  /* Karten-Info für Kontrollanzeigen (Name, Seltenheit, Bild-Kandidaten) */
  function cardInfo(set, n){
    const e = findCardIn(set, n);
    if (!e) return null;
    const name = (e[1] || ("Nr. " + pad(n))).replace(/-/g, " ");
    let rarity = e[3] || "";
    if (!rarity && /-ex/i.test(e[1])) rarity = "ex";
    return { name, rarity, urls: imgCandidatesFor(set, n) };
  }

  global.Shared = {
    pad, kartencode, localImgPath,
    findCardIn, setByCodeLang, findSetByCode,
    imgCandidatesFor, cardInfo
  };

})(typeof window !== "undefined" ? window : globalThis);
