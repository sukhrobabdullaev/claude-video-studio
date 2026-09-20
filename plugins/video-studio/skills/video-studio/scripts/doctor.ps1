# Thin bootstrap for Windows. The checks live in doctor.py.
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $dir "doctor.py"
$vsHome = if ($env:VS_HOME) { $env:VS_HOME } else { Join-Path $HOME ".video-studio" }
$venvPy = Join-Path $vsHome "venv\Scripts\python.exe"

if (Test-Path $venvPy) { & $venvPy $script @args; exit $LASTEXITCODE }

$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if ($py) { & $py.Source $script @args; exit $LASTEXITCODE }

if (Get-Command uv -ErrorAction SilentlyContinue) {
  & uv run --no-project --python 3.12 $script @args; exit $LASTEXITCODE
}

Write-Host "  FAIL  neither a python nor uv is installed"
Write-Host "        -> winget install astral-sh.uv, then run scripts\setup.ps1"
exit 1
