# Run any bundled python script with the project environment and API keys loaded.
#
#   powershell -File scripts\vs.ps1 transcribe.py clip.mov --audio-track 0
#   powershell -File scripts\vs.ps1 edit\animations\make_label.py   (a script you wrote)
#
# Both venv layouts are accepted so this also runs under PowerShell on macOS and
# Linux — which is how it gets tested away from a Windows machine.
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Windows consoles default to a legacy code page, so any script printing an arrow or
# an em dash dies with UnicodeEncodeError. UTF-8 mode makes output identical on all
# three platforms.
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$vsHome = if ($env:VS_HOME) { $env:VS_HOME } else { Join-Path $HOME ".video-studio" }

$py = $null
foreach ($candidate in @((Join-Path $vsHome "venv/Scripts/python.exe"),
                         (Join-Path $vsHome "venv/bin/python"))) {
  if (Test-Path $candidate) { $py = $candidate; break }
}
if (-not $py) {
  Write-Error ("python env missing - run: powershell -File " + (Join-Path $dir "setup.ps1"))
  exit 1
}

$envFile = Join-Path $vsHome ".env"
if (Test-Path $envFile) {
  Get-Content $envFile | Where-Object { $_ -match "^\s*[A-Za-z_][A-Za-z0-9_]*=" } | ForEach-Object {
    $name, $value = $_ -split "=", 2
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
  }
}

if ($args.Count -eq 0) {
  Write-Host "usage: vs.ps1 <script> [args]"
  Write-Host ("bundled: " + ((Get-ChildItem (Join-Path $dir "*.py")).Name -join " "))
  Write-Host "or pass a path to a script you wrote (resolved from the current directory)"
  exit 2
}

$script = $args[0]
# @(...) is load-bearing: with exactly one remaining argument PowerShell returns a
# bare string, and splatting a string spreads it one character per argument.
$rest = @($args | Select-Object -Skip 1)
$bundled = Join-Path $dir $script
if (Test-Path $bundled) { & $py $bundled @rest }
elseif (Test-Path $script) { & $py $script @rest }
else {
  Write-Error "no such script: $script"
  exit 1
}
exit $LASTEXITCODE
