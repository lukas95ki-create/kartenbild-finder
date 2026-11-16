# Dumps, per downloaded page, the ordered sequence of headings and upload image base names.
param([string]$HtmlDir, [string]$OutDir)
New-Item -ItemType Directory -Force $OutDir | Out-Null
$rx = [regex]'(?s)<(h[1-4])[^>]*>(.*?)</\1>|https://pokezentrum\.de/wp-content/uploads/([^"''\s?)<>\\]+?\.(?:jpg|jpeg|png|webp))'
foreach ($f in Get-ChildItem $HtmlDir -Filter *.html) {
  if ($f.Length -lt 1000) { continue }
  $t = [Net.WebUtility]::HtmlDecode([IO.File]::ReadAllText($f.FullName, [Text.Encoding]::UTF8))
  $t = [regex]::Replace($t, '(?s)<script.*?</script>|<style.*?</style>', '')
  $seen = @{}
  $out = New-Object System.Collections.Generic.List[string]
  foreach ($m in $rx.Matches($t)) {
    if ($m.Groups[1].Success) {
      $h = ([regex]::Replace($m.Groups[2].Value, '<[^>]+>', '')).Trim() -replace '\s+', ' '
      if ($h) { $out.Add("H: $h") }
    } else {
      $n = $m.Groups[3].Value
      $n = $n -replace '-\d{2,4}x\d{2,4}(\.\w+)$', '$1'
      $n = $n -replace '-scaled(\.\w+)$', '$1'
      if (-not $seen.ContainsKey($n)) { $seen[$n] = 1; $out.Add($n) }
    }
  }
  [IO.File]::WriteAllLines((Join-Path $OutDir ($f.BaseName + '.txt')), $out, (New-Object Text.UTF8Encoding $false))
}
