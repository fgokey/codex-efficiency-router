$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'cer.ps1') install @args
exit $LASTEXITCODE
