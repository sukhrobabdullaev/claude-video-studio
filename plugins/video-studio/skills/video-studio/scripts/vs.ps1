# Run any bundled python script with the project environment and API keys loaded.
#
#   powershell -File scripts\vs.ps1 transcribe.py clip.mov --audio-track 0
#   powershell -File scripts\vs.ps1 edit\animations\make_label.py   (your own script)
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$vsHome = if ($env:VS_HOME) { $env:VS_HOME } else { Join-Path $HOME ".video-studio" }
$py = Join-Path $vsHome "venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  Write-Error "python env missing - run: powershell -File $dir\setup.ps1"; exit 1
}
$envFile = Join-Path $vsHome ".env"
if (Test-Path $envFile) {
  Get-Content $envFile | Where-Object { $_ -match "^\s*[A-Z_]+=" } | ForEach-Object {
    $name, $value = $_ -split "=", 2
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
  }
}
if ($args.Count -eq 0) {
  Write-Host "usage: vs.ps1 <script> [args]"
  Write-Host ("bundled: " + ((Get-ChildItem (Join-Path $dir "*.py")).Name -join " "))
  exit 2
}
$script = $args[0]; $rest = $args[1..($args.Count-1)]
$bundled = Join-Path $dir $script
if (Test-Path $bundled) { & $py $bundled @rest }
elseif (Test-Path $script) { & $py $script @rest }
else { Write-Error "no such script: $script"; exit 1 }
exit $LASTEXITCODE
