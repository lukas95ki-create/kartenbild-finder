# Merges work\out\<code>.tsv into sets-data.js (data only), rewrites links\Deutsch-<code>.txt
# and writes work\merge-summary.tsv + work\missing.tsv for the report step.
param([string]$Work, [string]$Repo)
. (Join-Path $Work 'tools\config.ps1')
$utf8 = New-Object Text.UTF8Encoding $false
$BASEURL = 'https://pokezentrum.de/wp-content/uploads/'
$dataPath = Join-Path $Repo 'sets-data.js'
$js = [IO.File]::ReadAllText($dataPath, $utf8)
$nl = if ($js.Contains("`r`n")) { "`r`n" } else { "`n" }

function JStr([string]$s) { return '"' + $s.Replace('\', '\\').Replace('"', '\"') + '"' }
function Read-Tsv([string]$code) {
  $rows = @()
  foreach ($l in [IO.File]::ReadAllLines((Join-Path $Work "out\$code.tsv"), $utf8)) {
    if (-not $l) { continue }
    $p = $l.Split("`t")
    $rows += [pscustomobject]@{N = [int]$p[0]; Name = $p[1]; Cat = $p[2]; File = $p[3]; Src = $p[4]; Note = $p[5]}
  }
  return $rows
}
function Emit-Known($cards) { return '{' + (($cards | ForEach-Object { "$($_.N):" + (JStr $_.File) }) -join ',') + '}' }
function Emit-Cards($cards) { return '[' + (($cards | ForEach-Object { "[$($_.N)," + (JStr $_.Name) + ',null,' + (JStr $_.Cat) + ']' }) -join ',') + ']' }

$summary = New-Object System.Collections.Generic.List[string]
$missing = New-Object System.Collections.Generic.List[string]
$newEntries = New-Object System.Collections.Generic.List[string]
$order = 'SWSH01','SWSH02','SWSH03','SWSH03.5','SWSH04','SWSH04.5','SWSH05','SWSH06','SWSH07','CEL','CEL-CC','SWSH08','SWSH09','SWSH10','PGO','SWSH11','SWSH11-TG','SWSH12','SWSH12.5','POR','PBL','30C','30C-CC','DLR'
$sorted = @($SETS | Where-Object { -not $_.New }) + @($order | ForEach-Object { $c = $_; $SETS | Where-Object { $_.Code -eq $c } })
if ($sorted.Count -ne $SETS.Count) { throw "order list does not cover all sets" }

foreach ($set in $sorted) {
  $rows = Read-Tsv $set.Code
  $name = $set.Name
  if ($set.New) {
    if ($js.Contains('{code:"' + $set.Code + '",')) { throw "set $($set.Code) already present" }
    $final = @($rows | Sort-Object N)
    $entry = '{code:' + (JStr $set.Code) + ',name:' + (JStr $set.Name) + ',lang:"Deutsch",total:' + $set.Total + ',page:' + (JStr $set.Page) + ',' + $nl + '  known:' + (Emit-Known $final) + ',' + $nl + '  cards:' + (Emit-Cards $final) + '}'
    $newEntries.Add($entry)
    $added = $final.Count; $before = 0
  } else {
    $rx = [regex]('(?s)(\{code:"' + [regex]::Escape($set.Code) + '",name:"([^"]*)",lang:"Deutsch",total:\d+,page:"[^"]*",\s*known:)\{(.*?)\}(,\s*cards:)\[(.*?)\]\}')
    $m = $rx.Match($js)
    if (-not $m.Success) { throw "existing set $($set.Code) not found" }
    $name = $m.Groups[2].Value
    $exKnown = @{}; foreach ($k in [regex]::Matches($m.Groups[3].Value, '(\d+):"((?:[^"\\]|\\.)*)"')) { $exKnown[[int]$k.Groups[1].Value] = $k.Groups[2].Value }
    $exCards = @(); foreach ($c in [regex]::Matches($m.Groups[5].Value, '\[(\d+),"((?:[^"\\]|\\.)*)",null,"([^"]*)"\]')) {
      $n = [int]$c.Groups[1].Value
      $exCards += [pscustomobject]@{N = $n; Name = $c.Groups[2].Value; Cat = $c.Groups[3].Value; File = $exKnown[$n]; Note = ''}
    }
    if ($exCards.Count -ne $exKnown.Count) { throw "$($set.Code): cards/known mismatch $($exCards.Count)/$($exKnown.Count)" }
    $files = @{}; foreach ($v in $exKnown.Values) { $files[$v] = 1 }
    $add = @()
    foreach ($r in $rows) {
      if ($exKnown.ContainsKey($r.N) -or $exKnown.ContainsKey($r.N + 1000) -or $files.ContainsKey($r.File)) { continue }
      $add += $r; $files[$r.File] = 1
    }
    $before = $exCards.Count; $added = $add.Count
    $final = @(@($exCards) + @($add) | Sort-Object N)
    if ($added -gt 0) {
      $repl = $m.Groups[1].Value + (Emit-Known $final) + $m.Groups[4].Value + (Emit-Cards $final) + '}'
      $js = $js.Substring(0, $m.Index) + $repl + $js.Substring($m.Index + $m.Length)
    }
  }
  # links file (one URL per card, card order)
  $lp = Join-Path $Repo ("links\Deutsch-" + $set.Code + ".txt")
  [IO.File]::WriteAllText($lp, ((($final | ForEach-Object { $BASEURL + $_.File }) -join "`n") + "`n"), $utf8)
  # gaps
  $have = @{}; foreach ($c in $final) { $have[$c.N] = 1 }
  $real = @($final | Where-Object { $_.N -lt 1000 } | ForEach-Object { $_.N })
  $max = ($real | Measure-Object -Maximum).Maximum
  $gapB = @(1..$set.Total | Where-Object { -not $have.ContainsKey($_) })
  $gapS = @(); if ($max -gt $set.Total) { $gapS = @(($set.Total + 1)..$max | Where-Object { -not $have.ContainsKey($_) -and -not $have.ContainsKey($_ + 1000) }) }
  foreach ($g in $gapB) { $missing.Add("Deutsch`t$($set.Code)`t$name`tNr.$('{0:000}' -f $g)`tkein Bild in Galerie/SR-Artikel gefunden") }
  foreach ($g in $gapS) { $missing.Add("Deutsch`t$($set.Code)`t$name`tNr.$('{0:000}' -f $g)`tkein Bild in Galerie/SR-Artikel gefunden (Secret Rare)") }
  $eng = @($rows | Where-Object { $_.Note -match 'englisches' -and $have.ContainsKey($_.N) -and (($final | Where-Object N -eq $_.N).File -eq $_.File) })
  foreach ($e in $eng) { $missing.Add("Deutsch`t$($set.Code)`t$name`tNr.$('{0:000}' -f $e.N) ($($e.Name))`tnur englisches Bild in der Galerie: $BASEURL$($e.File)") }
  $sec = @($final | Where-Object { $_.Cat -in 'AR','SAR','SR','UR' }).Count
  $summary.Add(("{0}`t{1}`t{2}`t{3}`t{4}`t{5}`t{6}`t{7}`t{8}" -f $set.Code, $name, $(if ($set.New) { 'neu' } else { 'vorhanden' }), $before, $added, $final.Count, $sec, ($gapB.Count + $gapS.Count), $eng.Count))
}

# insert the new sets behind the last German set (before the first Chinese set)
$anchor = '{code:"CBB1C"'
$i = $js.IndexOf($anchor)
if ($i -lt 0) { throw 'anchor CBB1C not found' }
$js = $js.Substring(0, $i) + (($newEntries -join (',' + $nl)) + ',' + $nl) + $js.Substring($i)
[IO.File]::WriteAllText($dataPath, $js, $utf8)
[IO.File]::WriteAllLines((Join-Path $Work 'merge-summary.tsv'), $summary, $utf8)
[IO.File]::WriteAllLines((Join-Path $Work 'missing.tsv'), $missing, $utf8)
"Code`tName`tStatus`tvorher`tneu dazu`tgesamt`tSecret`tLuecken`tnur EN"
$summary
