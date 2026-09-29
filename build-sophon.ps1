$ErrorActionPreference = 'Stop'
$Python = if ($env:SOPHON_PYTHON) { $env:SOPHON_PYTHON } else { 'python' }
& $Python (Join-Path $PSScriptRoot 'build.py') @args
exit $LASTEXITCODE
