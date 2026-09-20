# Thin bootstrap for Windows. The install logic lives in setup.py.
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = (Get-Command py -ErrorAction SilentlyContinue) ?? (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) { Write-Error "Python 3 is required. Install it from python.org, then re-run."; exit 1 }
& $py.Source (Join-Path $dir "setup.py") @args
exit $LASTEXITCODE
