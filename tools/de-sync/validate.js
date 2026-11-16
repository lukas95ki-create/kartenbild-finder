// cscript validation: loads sets-data.js and checks structural consistency.
var path = WScript.Arguments(0);
var st = new ActiveXObject("ADODB.Stream");
st.Type = 2; st.Charset = "utf-8"; st.Open(); st.LoadFromFile(path);
var src = st.ReadText(); st.Close();
eval(src);
var langs = {}, problems = 0, codes = {};
for (var i = 0; i < SETS.length; i++) {
  var s = SETS[i];
  langs[s.lang] = (langs[s.lang] || 0) + 1;
  var key = s.lang + "|" + s.code;
  if (codes[key]) { WScript.Echo("DUPLICATE SET " + key); problems++; }
  codes[key] = 1;
  if (!s.cards || !s.cards.length) { WScript.Echo("NO CARDS " + key); problems++; continue; }
  var seen = {};
  for (var j = 0; j < s.cards.length; j++) {
    var c = s.cards[j];
    if (seen[c[0]]) { WScript.Echo("DUP CARD " + key + " " + c[0]); problems++; }
    seen[c[0]] = 1;
    if (typeof c[1] !== "string" || !c[1]) { WScript.Echo("BAD NAME " + key + " " + c[0]); problems++; }
    if (s.lang === "Deutsch") {
      if (!s.known || !s.known[c[0]]) { WScript.Echo("NO IMAGE " + key + " " + c[0]); problems++; }
      else if (!/\.(jpg|jpeg|png|webp)$/.test(s.known[c[0]])) { WScript.Echo("BAD FILE " + key + " " + c[0]); problems++; }
    }
  }
}
var out = "sets=" + SETS.length;
for (var l in langs) out += " " + l + "=" + langs[l];
WScript.Echo(out + " problems=" + problems + " BASE=" + BASE);
