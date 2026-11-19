$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
uv sync --locked --group build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run --no-sync python scripts/build.py
exit $LASTEXITCODE
