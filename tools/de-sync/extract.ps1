# Extracts card number / name / category / exact filename per set from the page dumps.
# Writes work\out\<code>.tsv (n, name, cat, filename, source, note) and prints a diagnostic report.
param([string]$Work, [string]$Only = '')
. (Join-Path $Work 'tools\config.ps1')
$dumpDir = Join-Path $Work 'dump'
$outDir = Join-Path $Work 'out'
New-Item -ItemType Directory -Force $outDir | Out-Null
$utf8 = New-Object Text.UTF8Encoding $false
$JUNK = 'Kartenliste|Logo|Booster|Display|Box|Top-10|Rangliste|Kollektion|Deck|kaufen|Uebersicht|Ueberblick|Banner|Blister|wertvollsten|Secret-Rare-Karten|Full-Art-Karten|Erweiterung-Produkte|Set-Erweiterung-Mega|Galer|-neu-20\d\d|Secret-Illustration-Rare-Full-Art'
$SKIP = 'SVP-DE|SVP-EN|MEP-|SWSH\d{3}|MEE-\d|Store-Promo'
$ENG = 'Englisch|[-_]EN[-_]|SV1EN'

function Get-Cat([string]$fn, [string]$heading, [int]$n, [int]$total, [string]$name) {
  foreach ($s in @($fn, ($heading -replace '\s+', '-'))) {
    if (-not $s) { continue }
    if ($s -cmatch 'Hyper-Rare|Gold-Rare|Rainbow|Regenbogen|Golden|(?<![A-Za-z])Gold(?![a-z])|[-_](MUR|UR|HR)[-_]') { return 'UR' }
    if ($s -match 'Sp\w*-Illustration|Special-Art|[-_]SAR[-_]') { return 'SAR' }
    if ($s -match 'Full-Art|Ultra-Rare|[-_]SR[-_]') { return 'SR' }
    if ($s -match 'Illustration-Rare|Art-Rare|[-_]AR[-_]') { return 'AR' }
    if ($n -le $total) { break }
  }
  if ($n -gt $total) { return 'SR' }
  if ($name -match '(^|-)ex($|-)') { return 'ex' }
  return ''
}

function Clean-Name([string]$raw, [string]$marker) {
  $s = $raw -replace '^Pokemon-Karte[-_](Unterstuetzer-|Stadion-|Item-)?', ''
  $m = [regex]::Match($s, "[-_]+(?:$marker|SV1DE|SV01DE|SV1EN|Crown_Zenith|PAF-DE|PAR-DE|JTG-DE)")
  if ($m.Success -and $m.Index -gt 0) { $s = $s.Substring(0, $m.Index) }
  $s = $s -replace '[-_]\d{3}$', ''
  return ($s -replace '_', '-').Trim('-')
}

# Fallback number detection for irregular filenames (site typos). Returns @(n, rawName) or $null.
function Get-Fallback([string]$fn, [int]$total) {
  $stem = $fn -replace '\.(jpg|jpeg|png|webp)$', ''
  $t3 = '{0:000}' -f $total
  $m = [regex]::Match($stem, '^(?<n>\d{3})[-_](?<name>.+)$')
  if ($m.Success) { return @([int]$m.Groups['n'].Value, $m.Groups['name'].Value) }
  $m = [regex]::Match($stem, '^(?<name>.+)[-_](?<n>\d{2,3})$')
  if ($m.Success) { return @([int]$m.Groups['n'].Value, $m.Groups['name'].Value) }
  $toks = @([regex]::Matches($stem, '(?<![A-Za-z0-9.])\d{2,3}(?![A-Za-z0-9.])') | Where-Object { $_.Value -ne $t3 -and $_.Value -ne "$total" -and $_.Value -ne '151' })
  if ($toks.Count -eq 1) {
    $i = $toks[0].Index
    $name = if ($i -gt 0) { $stem.Substring(0, $i) } else { $stem.Substring($toks[0].Length) }
    return @([int]$toks[0].Value, $name.Trim('-_'))
  }
  return $null
}

function Same-Card([string]$a, [string]$b) {
  $x = ($a -replace '[^A-Za-z]', '').ToLower(); $y = ($b -replace '[^A-Za-z]', '').ToLower()
  if (-not $x -or -not $y) { return $false }
  if ($x.Contains($y) -or $y.Contains($x)) { return $true }
  # tolerate small spelling differences (Piccochilla / Picochilla)
  if ([Math]::Abs($x.Length - $y.Length) -le 2 -and $x.Length -ge 5) {
    $k = 0; while ($k -lt $x.Length -and $k -lt $y.Length -and $x[$k] -eq $y[$k]) { $k++ }
    if ($k -ge [Math]::Min($x.Length, $y.Length) - 3 -and $k -ge 3) { return $true }
  }
  return $false
}

$report = New-Object System.Collections.Generic.List[string]
foreach ($set in $SETS) {
  if ($Only -and $set.Code -ne $Only) { continue }
  $sources = @(@{File = $set.G; Shared = [bool]$set.MAll})
  foreach ($s in $set.S) { $sources += @{File = $s; Shared = [bool]$set.MAll} }
  if (-not $set.Seq -and -not $set.NoOverview) { $sources += @{File = $IR; Shared = $true}; $sources += @{File = $SIR; Shared = $true} }
  $byNum = @{}
  $pending = New-Object System.Collections.Generic.List[object]
  $notes = New-Object System.Collections.Generic.List[string]
  $unmatched = New-Object System.Collections.Generic.List[string]
  $seq = 0
  foreach ($src in $sources) {
    $p = Join-Path $dumpDir ($src.File + '.txt')
    if (-not (Test-Path $p)) { $report.Add("  !! missing dump $($src.File)"); continue }
    $heading = ''; $prev = 0
    $isGallery = ($src.File -eq $set.G)
    foreach ($line in [IO.File]::ReadAllLines($p, $utf8)) {
      if ($line.StartsWith('H: ')) { $heading = $line.Substring(3); continue }
      if ($line -notmatch '\.(jpg|jpeg|png|webp)$') { continue }
      if ($set.Sect -and $isGallery -and $heading -notmatch $set.Sect) { continue }
      if ($set.Seq) {
        if ($line -notmatch $set.M -or $line -match $JUNK) { continue }
        $seq++
        $nm = ([regex]::Split($line, '[-_]\d')[0] -replace '_', '-').Trim('-')
        $byNum[$seq] = @{N = $seq; Name = $nm; Cat = ''; File = $line; Src = $src.File; Note = 'laufende Nummer (Reihenfolge der Galerie)'; Eng = $false; Heading = $heading}
        continue
      }
      if ($src.Shared -and $line -notmatch $set.M) { continue }
      if ($line -match $SKIP) { continue }
      if ($set.Ex -and $line -match $set.Ex) { continue }
      $n = $null; $name = $null; $fb = $false
      if ($set.Fix -and $set.Fix.ContainsKey($line)) { $n = [int]$set.Fix[$line]; $name = Clean-Name ([regex]::Split($line, '[-_]\d')[0]) $set.M }
      if ($null -eq $n) {
        foreach ($rx in $set.Rx) { $mm = [regex]::Match($line, $rx); if ($mm.Success) { $n = [int]$mm.Groups['n'].Value; $name = Clean-Name $mm.Groups['name'].Value $set.M; break } }
      }
      if ($null -eq $n) {
        if ($src.Shared -or $set.NoFallback -or $line -notmatch $set.M -or $line -match $JUNK) { continue }
        $r = Get-Fallback $line $set.Total
        if ($null -eq $r) { if ($line -match '\d{2}') { $unmatched.Add($line) }; continue }
        $n = $r[0]; $name = Clean-Name $r[1] $set.M; $fb = $true
      }
      if ($n -lt 1 -or $n -gt 400) { $unmatched.Add($line); continue }
      $rec = @{N = $n; Name = $name; Cat = ''; File = $line; Src = $src.File; Note = $(if ($fb) { 'Fallback-Muster' } else { '' }); Eng = ($line -match $ENG); Heading = $heading; Prev = $prev; Gal = (-not $src.Shared)}
      if ($byNum.ContainsKey($n)) {
        $old = $byNum[$n]
        if ($old.File -eq $line) { $prev = $n; continue }
        if ($old.Eng -and -not $rec.Eng) { $rec.Prev = $old.Prev; $byNum[$n] = $rec; $prev = $n; continue }   # prefer the German image
        if ($rec.Eng -or (Same-Card $old.Name $name)) { continue }     # alternative image of the same card
        $pending.Add($rec); continue
      }
      $byNum[$n] = $rec; $prev = $n
    }
  }
  foreach ($rec in $pending) {
    $cand = $rec.Prev + 1
    $em = [regex]::Match($rec.File, '^[^-_]+[-_](\d{3})[-_]\d{3}-\d{3}[-_]')
    if ($em.Success -and -not $byNum.ContainsKey([int]$em.Groups[1].Value)) { $cand = [int]$em.Groups[1].Value }
    $k = 0; while ($k -lt 4 -and $byNum.ContainsKey($cand) -and $byNum[$cand].Note -like 'Nr. laut*') { $cand++; $k++ }
    if ($rec.Gal -and $rec.Prev -gt 0 -and -not $byNum.ContainsKey($cand)) {
      $notes.Add("    fix: '$($rec.File)' traegt Nr. $($rec.N) (doppelt) -> Nr. $cand nach Galerie-Position")
      $rec.Note = "Nr. laut Galerie-Position (Dateiname sagt $($rec.N))"; $rec.N = $cand; $byNum[$cand] = $rec
    } else {
      $notes.Add("    DUP unresolved $($rec.N): $($byNum[$rec.N].File) <> $($rec.File)")
    }
  }
  foreach ($r in $byNum.Values) { if (-not $set.Seq) { $r.Cat = Get-Cat $r.File $r.Heading $r.N $set.Total $r.Name } }
  $nums = @($byNum.Keys | Sort-Object)
  $rows = foreach ($n in $nums) {
    $r = $byNum[$n]; $nt = $r.Note
    if ($r.Eng) { $nt = (@($nt, 'nur englisches Bild') | Where-Object { $_ }) -join '; ' }
    "$($r.N)`t$($r.Name)`t$($r.Cat)`t$($r.File)`t$($r.Src)`t$nt"
  }
  [IO.File]::WriteAllLines((Join-Path $outDir ($set.Code + '.tsv')), [string[]]@($rows), $utf8)
  $base = @($nums | Where-Object { $_ -le $set.Total })
  $sec = @($nums | Where-Object { $_ -gt $set.Total })
  $missing = @(1..$set.Total | Where-Object { -not $byNum.ContainsKey($_) })
  $secMax = if ($sec.Count) { ($sec | Measure-Object -Maximum).Maximum } else { $set.Total }
  $secMissing = @(); if ($sec.Count) { $secMissing = @(($set.Total + 1)..$secMax | Where-Object { -not $byNum.ContainsKey($_) }) }
  $cats = ($byNum.Values | Group-Object { $_.Cat } | Sort-Object Name | ForEach-Object { "$($_.Name)=$($_.Count)" }) -join ' '
  $report.Add(("{0,-9} total={1,-3} base={2,-3} secret={3,-3} max={4,-3} missBase={5} missSecret={6} cats[{7}]" -f $set.Code, $set.Total, $base.Count, $sec.Count, $secMax, $missing.Count, $secMissing.Count, $cats))
  if ($missing.Count) { $report.Add("    missing base: " + ($missing -join ',')) }
  if ($secMissing.Count) { $report.Add("    missing secret: " + ($secMissing -join ',')) }
  foreach ($d in $notes) { $report.Add($d) }
  foreach ($u in $unmatched | Select-Object -Unique | Select-Object -First 6) { $report.Add("    unmatched $u") }
  $fbs = @($byNum.Values | Where-Object { $_.Note -eq 'Fallback-Muster' })
  if ($fbs.Count) { $report.Add("    fallback-matched: $($fbs.Count)  e.g. " + ((@($fbs | Select-Object -First 3 | ForEach-Object { "$($_.N)=$($_.File)" })) -join ' | ')) }
  $engc = @($byNum.Values | Where-Object { $_.Eng }).Count
  if ($engc) { $report.Add("    english-only images: $engc") }
}
$report
