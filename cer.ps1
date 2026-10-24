# Explicit local launcher. Host persistence is opt-in; no Hook trust or model changes.
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

function Get-CerUserCli {
    [Environment]::GetEnvironmentVariable('CODEX_CLI_PATH', 'User')
}

function Set-CerUserCli {
    param([AllowNull()][string]$Value)
    # The Windows API also broadcasts WM_SETTINGCHANGE to refresh Explorer.
    [Environment]::SetEnvironmentVariable('CODEX_CLI_PATH', $Value, 'User')
}

function Get-CerHostSelectionPath {
    $SelectionRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else {
        Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex'
    }
    if (-not [IO.Path]::IsPathRooted($SelectionRoot)) { throw 'CODEX_HOME must be absolute for host selection.' }
    Join-Path $SelectionRoot 'hosts/selection.json'
}

function Read-CerHostSelection {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    if ((Get-Item -LiteralPath $Path).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'Host selection record must not be a link.'
    }
    $Record = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    if ($Record.owner -ne 'cer-native-host-selection' -or $Record.schema -ne 1 -or
        -not $Record.cli -or -not [IO.Path]::IsPathRooted($Record.cli) -or
        'previous_cli' -notin $Record.PSObject.Properties.Name -or
        ($null -ne $Record.previous_cli -and $Record.previous_cli -isnot [string]) -or
        ('transition_cli' -in $Record.PSObject.Properties.Name -and
         $null -ne $Record.transition_cli -and $Record.transition_cli -isnot [string])) {
        throw 'Unowned or invalid host selection record; nothing was changed.'
    }
    return $Record
}

function Write-CerHostSelection {
    param([string]$Path, $Record)
    $Directory = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    $Temporary = Join-Path $Directory ([Guid]::NewGuid().ToString() + '.tmp')
    try {
        [IO.File]::WriteAllText($Temporary, ($Record | ConvertTo-Json -Compress),
            [Text.UTF8Encoding]::new($false))
        if (Test-Path -LiteralPath $Path) { [IO.File]::Replace($Temporary, $Path, [NullString]::Value) }
        else { [IO.File]::Move($Temporary, $Path) }
    } finally {
        if (Test-Path -LiteralPath $Temporary) { Remove-Item -LiteralPath $Temporary }
    }
}

function Resolve-CerDesktop {
    param([string]$ExplicitPath)
    if ($ExplicitPath) {
        if (-not [IO.Path]::IsPathRooted($ExplicitPath) -or
            -not (Test-Path -LiteralPath $ExplicitPath -PathType Leaf)) {
            throw 'Desktop path no longer exists or is not absolute. Omit it to discover the current installed package.'
        }
        return $ExplicitPath
    }
    $Packages = @(Get-AppxPackage -Name OpenAI.Codex -ErrorAction Stop |
        Sort-Object { [version]$_.Version } -Descending)
    if ($Packages.Count -eq 0) { throw 'No installed OpenAI.Codex desktop package found.' }
    $DesktopPath = Join-Path $Packages[0].InstallLocation 'app/ChatGPT.exe'
    if (-not (Test-Path -LiteralPath $DesktopPath -PathType Leaf)) {
        throw 'The current desktop package is incomplete; no older-package fallback is allowed.'
    }
    return $DesktopPath
}

function Invoke-CerHost {
    param([string[]]$Arguments)
    if (Test-Path -LiteralPath (Join-Path $Root '.cer-install.json')) {
        throw 'Run host selection from the source checkout; Skill installation does not select a host.'
    }
    $Options = @($Arguments | Where-Object { $_.StartsWith('--') })
    if (@($Options | Select-Object -Unique).Count -ne $Options.Count -or
        @($Options | Where-Object { $_ -notin @('--dry-run', '--persist', '--restore') }).Count) {
        throw 'Unknown or duplicate host option.'
    }
    $Positional = @($Arguments | Where-Object { -not $_.StartsWith('--') })
    $Preview = '--dry-run' -in $Options
    $Persist = '--persist' -in $Options
    $Restore = '--restore' -in $Options
    if ($Positional.Count -gt 2 -or ($Restore -and ($Persist -or $Positional.Count))) {
        throw 'Usage: cer.ps1 host [<bundle> [<desktop.exe>]] [--persist] [--dry-run], or host --restore [--dry-run]'
    }
    $SelectionPath = Get-CerHostSelectionPath
    $Selection = Read-CerHostSelection $SelectionPath
    if ($Restore) {
        if ($null -eq $Selection) { throw 'No owned host selection to restore.' }
        $Current = Get-CerUserCli
        if ($Current -cne $Selection.cli -and $Current -cne $Selection.previous_cli -and
            ('transition_cli' -notin $Selection.PSObject.Properties.Name -or
             $Current -cne $Selection.transition_cli)) {
            throw 'User CODEX_CLI_PATH changed outside this installer; preserving it and its backup.'
        }
        if (-not $Preview) {
            Set-CerUserCli $Selection.previous_cli
            if ((Get-CerUserCli) -cne $Selection.previous_cli) { throw 'Host selection restore did not persist.' }
            Remove-Item -LiteralPath $SelectionPath
        }
        [pscustomobject]@{status=$(if ($Preview) {'RESTORE_PREVIEW'} else {'RESTORED'});
            cli=$Selection.previous_cli; restart_required=$true} | ConvertTo-Json -Compress
        return
    }
    $Bundle = if ($Positional.Count) { $Positional[0] } elseif ($null -ne $Selection) {
        if ((Get-CerUserCli) -cne $Selection.cli) {
            throw 'User CODEX_CLI_PATH changed outside this installer; refusing the saved selection.'
        }
        Split-Path -Parent $Selection.cli
    } else { throw 'Supply a host bundle first; no persistent host selection exists.' }
    if (-not [IO.Path]::IsPathRooted($Bundle)) { throw 'An absolute host bundle path is required.' }
    $ExplicitDesktop = if ($Positional.Count -eq 2) { $Positional[1] } else { $null }
    $Desktop = Resolve-CerDesktop $ExplicitDesktop
    if ((Get-Item -LiteralPath $Bundle).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'Host bundle must not be a link.'
    }
    $Manifest = Get-Content -LiteralPath (Join-Path $Bundle 'install.json') -Raw | ConvertFrom-Json
    if ($Manifest.owner -ne 'cer-native-admission-host' -or $Manifest.admission_contract -ne 2) {
        throw 'A current, tested admission host bundle is required; legacy manifests are insufficient.'
    }
    $Files = @($Manifest.files.PSObject.Properties)
    foreach ($Required in @('codex.exe', 'codex.pdb', 'codex-app-server.exe', 'codex_app_server.pdb',
                           'codex-code-mode-host.exe')) {
        if ($Required -notin $Files.Name) { throw "Host manifest is missing $Required." }
    }
    foreach ($File in $Files) {
        if ([IO.Path]::GetFileName($File.Name) -cne $File.Name -or
            $File.Value -notmatch '^[0-9a-f]{64}$') { throw 'Invalid host manifest entry.' }
        $Item = Join-Path $Bundle $File.Name
        if (-not (Test-Path -LiteralPath $Item -PathType Leaf) -or
            (Get-Item -LiteralPath $Item).Attributes -band [IO.FileAttributes]::ReparsePoint -or
            (Get-FileHash -LiteralPath $Item -Algorithm SHA256).Hash.ToLowerInvariant() -cne $File.Value) {
            throw "Host bundle changed or is missing: $($File.Name). No desktop fallback is allowed."
        }
    }
    $Cli = Join-Path $Bundle 'codex.exe'
    if ($Persist) {
        $Current = Get-CerUserCli
        if ($null -ne $Selection -and $Current -cne $Selection.cli -and
            ('transition_cli' -notin $Selection.PSObject.Properties.Name -or
             $Current -cne $Selection.transition_cli)) {
            throw 'User CODEX_CLI_PATH changed outside this installer; preserving it and its backup.'
        }
        $Previous = if ($null -ne $Selection) { $Selection.previous_cli } else { $Current }
        if (-not $Preview) {
            $Record = [pscustomobject]@{owner='cer-native-host-selection'; schema=1;
                cli=$Cli; previous_cli=$Previous}
            $Transition = [pscustomobject]@{owner=$Record.owner; schema=$Record.schema;
                cli=$Cli; previous_cli=$Previous; transition_cli=$Current}
            Write-CerHostSelection $SelectionPath $Transition
            try {
                Set-CerUserCli $Cli
                if ((Get-CerUserCli) -cne $Cli) { throw 'User host selection did not persist.' }
                Write-CerHostSelection $SelectionPath $Record
            } catch {
                if ((Get-CerUserCli) -ceq $Current) {
                    if ($null -ne $Selection) { Write-CerHostSelection $SelectionPath $Selection }
                    else { Remove-Item -LiteralPath $SelectionPath }
                }
                throw
            }
        }
        [pscustomobject]@{status=$(if ($Preview) {'PERSIST_PREVIEW'} else {'PERSISTED_RESTART_REQUIRED'});
            cli=$Cli; desktop=$Desktop; previous_cli=$Previous; live_admission='UNKNOWN';
            action='At a safe boundary fully exit the desktop, then launch from the normal icon or cer.ps1 host.'} |
            ConvertTo-Json -Compress
        return
    }
    if ($Preview) {
        [pscustomobject]@{status='VERIFIED_FILES_ONLY'; cli=$Cli; desktop=$Desktop;
            live_admission='UNKNOWN'; action='Launch after all desktop chats reach a safe boundary and the app is closed'} |
            ConvertTo-Json -Compress
        return
    }
    if (Get-Process -Name codex,ChatGPT -ErrorAction SilentlyContinue) {
        throw 'Close the desktop app at a safe boundary first. No running process was stopped.'
    }
    $PreviousCli = $env:CODEX_CLI_PATH
    try {
        $env:CODEX_CLI_PATH = $Cli
        Start-Process -FilePath $Desktop | Out-Null
    } finally {
        $env:CODEX_CLI_PATH = $PreviousCli
    }
    Write-Output 'Desktop launched with the checked host. Verify native tools and binding before acceptance; use this entry for later launches.'
}

# Loading functions supports isolated OS-boundary tests without touching user settings.
if ($MyInvocation.InvocationName -eq '.') { return }
if ($args.Count -gt 0 -and [string]$args[0] -eq 'host') {
    Invoke-CerHost -Arguments @($args | Select-Object -Skip 1)
    exit 0
}

$Commands = @{
    install = 'install.py'; uninstall = 'uninstall.py'; doctor = 'doctor.py'
    guard = 'write_guard.py'; canary = 'canary.py'; compare = 'compare_runs.py'
    read = 'readonly_reader.py'
}
if ($args.Count -eq 0 -or -not $Commands.ContainsKey([string]$args[0])) {
    throw 'Usage: .\cer.ps1 <host|read|install|uninstall|doctor|guard|canary|compare> [script arguments]'
}
$Action = [string]$args[0]
$Forward = @($args | Select-Object -Skip 1)
if ($Action -ne 'read' -and (Test-Path -LiteralPath (Join-Path $Root '.cer-install.json') -PathType Leaf)) {
    throw 'Installed Skill launcher supports read only; run lifecycle commands from the source checkout.'
}
$Python = Resolve-CerPython
if ($Action -eq 'read') {
    $Reader = Join-Path $Root 'scripts/readonly_reader.py'
    if (-not (Test-Path -LiteralPath $Reader -PathType Leaf)) {
        $Reader = Join-Path $Root 'hooks/readonly_reader.py'
    }
    if (-not (Test-Path -LiteralPath $Reader -PathType Leaf)) { throw 'CER reader is missing.' }
    & $Python.executable -I -B $Reader @Forward
    exit $LASTEXITCODE
}
[Console]::Error.WriteLine(('CER Python {0}: {1}' -f ($Python.version -join '.'), $Python.executable))
# Do not use -I for these scripts: their own adjacent imports must remain available.
& $Python.executable -B (Join-Path $Root ('scripts/' + $Commands[$Action])) @Forward
exit $LASTEXITCODE
