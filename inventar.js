/* ============================================================
   inventar.js  —  Inventar-Modul (ARCHITEKTUR-V6, Kap. 2/13/14)
   Gemeinsame Bestandsquelle für Erfassung, eBay-Export und
   (später) Dashboard/Scanner. Speicherung: localStorage.

   Schema v2 je Eintrag (abwärtskompatibel migriert):
     id          stabile Kennung
     setCode/setName/lang/num/name/rarity   Kartendaten
     qty/status/price/note/manual/date      Bestandsdaten (wie v1;
                                            price = EINKAUFSpreis)
     kartencode  kanonisch "SETCODE-NNN"
     lagerplatz  z. B. "R2-B5-F12" (frei, leer erlaubt)
     owner       vorerst immer "local" (Mehrbenutzer-Vorbereitung)
     updatedAt   ISO-Zeitstempel der letzten Änderung
     version     Schema-Version des Eintrags (2)

   Der localStorage-Schlüssel bleibt der von v1 — die Migration
   passiert pro Eintrag beim Laden und ist idempotent.
   ============================================================ */
"use strict";
(function(global){

  const STORE_KEY      = "kartenErfassung.v1";
  const SCHEMA_VERSION = 2;
  const STATUSES       = ["Im Bestand", "Gelistet", "Verkauft"];

  function nowIso(){ return new Date().toISOString(); }
  function genId(){ return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }
  function pad3(n){ return String(n).padStart(3, "0"); }
  function codeOf(setCode, num){
    return String(setCode || "").toUpperCase() + "-" + pad3(parseInt(num, 10) || 0);
  }

  /* Einen Eintrag (v1 oder älter) auf Schema v2 heben — idempotent. */
  function migrateEntry(e){
    if (!e.id) e.id = genId();
    if (!e.kartencode) e.kartencode = codeOf(e.setCode, e.num);
    if (e.lagerplatz == null) e.lagerplatz = "";
    if (!e.owner) e.owner = "local";
    if (!e.updatedAt) e.updatedAt = e.date || nowIso();
    if (!e.version || e.version < SCHEMA_VERSION) e.version = SCHEMA_VERSION;
    return e;
  }

  /* Kompletten Bestand laden (immer bereits migriert). */
  function load(){
    let list;
    try { list = JSON.parse(global.localStorage.getItem(STORE_KEY)) || []; }
    catch (err){ list = []; }
    if (!Array.isArray(list)) list = [];
    return list.map(migrateEntry);
  }

  /* Bestand speichern. Wirft bei vollem Speicher — Aufrufer fängt ab. */
  function save(list){
    global.localStorage.setItem(STORE_KEY, JSON.stringify(list));
  }

  /* Duplikat-Erkennung: gleiche Karte = Set + Nummer + Sprache. */
  function findEntry(list, setCode, num, lang){
    return list.find(e => e.setCode === setCode && e.num === num && e.lang === lang);
  }

  /* Neuen Eintrag im Schema v2 anlegen. */
  function newEntry(o){
    return {
      id: genId(),
      setCode: o.setCode, setName: o.setName || "", lang: o.lang || "",
      num: o.num, name: o.name || ("Nr. " + pad3(o.num)), rarity: o.rarity || "",
      qty: (o.qty != null) ? o.qty : 1,
      status: STATUSES.includes(o.status) ? o.status : STATUSES[0],
      price: (o.price != null) ? o.price : null,
      note: o.note || "", manual: !!o.manual,
      date: o.date || nowIso(),
      kartencode: codeOf(o.setCode, o.num),
      lagerplatz: o.lagerplatz || "",
      owner: o.owner || "local",
      updatedAt: nowIso(),
      version: SCHEMA_VERSION
    };
  }

  /* Nach jeder Änderung aufrufen: Zeitstempel + kanonischen Code pflegen. */
  function touch(e){
    e.updatedAt = nowIso();
    e.kartencode = codeOf(e.setCode, e.num);
    return e;
  }

  /* Fremd-/Import-Daten (JSON-Backup) säubern und auf v2 heben. */
  function normalize(e){
    const num = parseInt(e.num, 10) || 0;
    return migrateEntry({
      id: e.id || genId(),
      setCode: String(e.setCode),
      setName: e.setName || "",
      lang: e.lang || "",
      num: num,
      name: e.name || ("Nr. " + pad3(num)),
      rarity: e.rarity || "",
      qty: parseInt(e.qty, 10) || 1,
      status: STATUSES.includes(e.status) ? e.status : STATUSES[0],
      price: (e.price != null && e.price !== "") ? (parseFloat(String(e.price).replace(",", ".")) || null) : null,
      note: e.note || "",
      manual: !!e.manual,
      date: e.date || nowIso(),
      lagerplatz: e.lagerplatz || "",
      owner: e.owner || "local",
      updatedAt: e.updatedAt || "",
      version: e.version || 0
    });
  }

  global.Inventar = {
    STORE_KEY, SCHEMA_VERSION, STATUSES,
    load, save, findEntry, newEntry, touch, normalize, migrateEntry, codeOf
  };

})(typeof window !== "undefined" ? window : globalThis);
