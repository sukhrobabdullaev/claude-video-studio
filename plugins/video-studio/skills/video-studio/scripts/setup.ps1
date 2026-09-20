# Thin bootstrap for Windows. The install logic lives in setup.py.
# No system Python needed: uv brings its own when none is installed.
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $dir "setup.py"

$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if ($py) { & $py.Source $script @args; exit $LASTEXITCODE }

if (Get-Command uv -ErrorAction SilentlyContinue) {
  & uv run --no-project --python 3.12 $script @args; exit $LASTEXITCODE
}

Write-Host "Install uv first, then re-run this script:"
Write-Host "    winget install astral-sh.uv"
Write-Host "(ffmpeg is also needed: winget install Gyan.FFmpeg)"
exit 1
