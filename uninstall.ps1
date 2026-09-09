$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'cer.ps1') uninstall @args
exit $LASTEXITCODE
