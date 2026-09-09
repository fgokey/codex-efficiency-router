# Explicit local launcher. No installs, PATH edits, Hook trust or model calls.
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$Root = $PSScriptRoot

function Test-CerPython {
    param([string]$Executable)
    $Probe = "import sys,json; sys.exit('Python 3.11+ is required') if sys.version_info < (3,11) else None; import tomllib; print(json.dumps({'executable':sys.executable,'version':list(sys.version_info[:3])}))"
    try {
        $Lines = @(& $Executable -I -B -c $Probe 2>$null)
        if ($LASTEXITCODE -ne 0) { return $null }
        $Info = ($Lines -join "`n") | ConvertFrom-Json -ErrorAction Stop
        if ($Info.version.Count -ne 3 -or $Info.version[0] -ne 3 -or $Info.version[1] -lt 11) { return $null }
        if (-not [IO.Path]::IsPathRooted($Info.executable) -or
            -not (Test-Path -LiteralPath $Info.executable -PathType Leaf)) { return $null }
        return $Info
    } catch {
        return $null
    }
}

function Resolve-CerPython {
    # An explicit override is authoritative: never silently switch away from it.
    if (-not [string]::IsNullOrWhiteSpace($env:CER_PYTHON)) {
        if (-not [IO.Path]::IsPathRooted($env:CER_PYTHON) -or
            -not (Test-Path -LiteralPath $env:CER_PYTHON -PathType Leaf)) {
            throw 'CER_PYTHON must be the full path to an existing Python 3.11+ executable.'
        }
        $Found = Test-CerPython $env:CER_PYTHON
        if ($null -eq $Found) { throw 'CER_PYTHON could not run Python 3.11+ with tomllib; no files changed.' }
        return $Found
    }
    # A command named python is not proof of a compatible runtime.
    foreach ($Name in @('python', 'python3')) {
        foreach ($Candidate in @(Get-Command $Name -CommandType Application -All -ErrorAction SilentlyContinue)) {
            $Found = Test-CerPython $Candidate.Source
            if ($null -ne $Found) { return $Found }
        }
    }
    # List installed runtimes only. Do not request a missing version or trigger downloads.
    foreach ($Launcher in @(Get-Command py -CommandType Application -All -ErrorAction SilentlyContinue)) {
        try { $Installed = @(& $Launcher.Source -0p 2>$null) } catch { continue }
        if ($LASTEXITCODE -ne 0) { continue }
        foreach ($Line in $Installed) {
            if ($Line -match '(?<exe>(?:[A-Za-z]:[\\/]|\\\\)[^"\r\n]*\.exe)"?\s*$') {
                $Found = Test-CerPython $Matches.exe
                if ($null -ne $Found) { return $Found }
            }
        }
    }
    throw 'No usable Python 3.11+ with tomllib found. Set CER_PYTHON to a verified full executable path; python/py defaults may be 3.10. Nothing was installed or changed.'
}

$Commands = @{
    install = 'install.py'; uninstall = 'uninstall.py'; doctor = 'doctor.py'
    guard = 'write_guard.py'; canary = 'canary.py'; compare = 'compare_runs.py'
}
if ($args.Count -eq 0 -or -not $Commands.ContainsKey([string]$args[0])) {
    throw 'Usage: .\cer.ps1 <install|uninstall|doctor|guard|canary|compare> [script arguments]'
}
$Action = [string]$args[0]
$Forward = @($args | Select-Object -Skip 1)
$Python = Resolve-CerPython
[Console]::Error.WriteLine(('CER Python {0}: {1}' -f ($Python.version -join '.'), $Python.executable))
# Do not use -I for these scripts: their own adjacent imports must remain available.
& $Python.executable -B (Join-Path $Root ('scripts/' + $Commands[$Action])) @Forward
exit $LASTEXITCODE
