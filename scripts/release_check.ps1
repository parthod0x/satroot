# Pre-release verification for SATROOT. Checks only — changes nothing.
#
#   powershell -ExecutionPolicy Bypass -File scripts\release_check.ps1
#
# Runs every gate that must pass before tagging, stops at the first failure,
# and prints the exact irreversible commands only if everything passed.
#
# ---------------------------------------------------------------------------
# WHY THIS IS A SCRIPT
# ---------------------------------------------------------------------------
# The release steps were handed over as a bash one-liner chain using `&&`,
# which Windows PowerShell 5.1 does not accept. It is a parse error, so the
# whole block was rejected and nothing ran — including the two verification
# steps at the top. That is the fourth mixed-shell failure in this project,
# and every previous one was fixed the same way: put it in a file.
#
# It deliberately does NOT tag, push or upload. Those are irreversible and
# belong to a human who has just read a passing report — not to a script that
# might be run by accident.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$failures = @()

function Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    try {
        & $Action
        if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
            throw "exit code $LASTEXITCODE"
        }
        Write-Host "  PASS" -ForegroundColor Green
    } catch {
        Write-Host "  FAIL: $_" -ForegroundColor Red
        $script:failures += $Name
    }
}

Write-Host "SATROOT pre-release check"
Write-Host "repo: $root"

# --- the version must agree with itself in all three places ---------------
Write-Host ""
Write-Host "=== declared version ===" -ForegroundColor Cyan
$pyproject = (Select-String -Path 'pyproject.toml' -Pattern '^version = "(.+)"').Matches.Groups[1].Value
$citation  = (Select-String -Path 'CITATION.cff'   -Pattern '^version: "(.+)"').Matches.Groups[1].Value
$changelog = (Select-String -Path 'CHANGELOG.md'   -Pattern '^## v(\S+)' | Select-Object -First 1).Matches.Groups[1].Value

Write-Host ("  pyproject.toml : {0}" -f $pyproject)
Write-Host ("  CITATION.cff   : {0}" -f $citation)
Write-Host ("  CHANGELOG.md   : {0}" -f $changelog)

if ($pyproject -ne $citation) {
    Write-Host "  FAIL: pyproject and CITATION disagree" -ForegroundColor Red
    $failures += 'version agreement'
} elseif (-not $changelog.StartsWith($pyproject)) {
    Write-Host "  FAIL: changelog's newest section is not $pyproject" -ForegroundColor Red
    $failures += 'version agreement'
} else {
    Write-Host "  PASS" -ForegroundColor Green
}

# --- a breaking release owes the reader a migration path ------------------
Write-Host ""
Write-Host "=== breaking-release paperwork ===" -ForegroundColor Cyan
if ($pyproject -match '^2\.' ) {
    $ok = $true
    if (-not (Test-Path 'MIGRATION.md')) {
        Write-Host "  FAIL: MIGRATION.md missing" -ForegroundColor Red; $ok = $false
    }
    if (-not (Select-String -Path 'README.md' -Pattern 'MIGRATION.md' -Quiet)) {
        Write-Host "  FAIL: README does not link MIGRATION.md" -ForegroundColor Red; $ok = $false
    }
    # The downstream pin. An open `>=` here is a scheduled outage: the next
    # image rebuild pulls the breaking version and the service comes up unable
    # to replay its own data, with nothing in any log to say why.
    $sl = Join-Path (Split-Path -Parent $root) 'satledger\pyproject.toml'
    if (Test-Path $sl) {
        if (Select-String -Path $sl -Pattern 'satroot\[.*\]>=[^,]*"' -Quiet) {
            Write-Host "  FAIL: satledger pins satroot with no upper bound" -ForegroundColor Red
            $ok = $false
        } else {
            Write-Host "  satledger ceiling present" -ForegroundColor Green
        }
    }
    if ($ok) { Write-Host "  PASS" -ForegroundColor Green } else { $failures += 'breaking paperwork' }
} else {
    Write-Host "  not a major version - skipped"
}

# --- the gates that actually execute code ---------------------------------
#
# Both are captured to log files rather than printed. The release gate emits
# megabytes of publication-workspace JSON, which on the first run overflowed
# the terminal's scrollback and carried the verdict away with it. A check you
# cannot find the result of has not checked anything.
$logDir = Join-Path $root '.release-logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$vectorLog = Join-Path $logDir "vectors-$stamp.log"
$gateLog   = Join-Path $logDir "release-gate-$stamp.log"

Step "conformance vectors" {
    python vectors/run.py 2>&1 | Tee-Object -FilePath $vectorLog | Select-String -Pattern 'vectors,|FAIL'
}

Write-Host ""
Write-Host "=== release gate (import smoke, operator proof, 1,766 tests) ===" -ForegroundColor Cyan
Write-Host "  this takes 15-25 minutes on this machine; output -> $gateLog"
python scripts/run_release_gate_smoke.py *> $gateLog
if ($LASTEXITCODE -eq 0) {
    Write-Host "  PASS" -ForegroundColor Green
} else {
    Write-Host "  FAIL (exit $LASTEXITCODE) - last 30 lines:" -ForegroundColor Red
    Get-Content $gateLog -Tail 30 | ForEach-Object { Write-Host "    $_" }
    $failures += 'release gate'
}

# --- nothing secret, nothing accidental -----------------------------------
Write-Host ""
Write-Host "=== working tree ===" -ForegroundColor Cyan
git status --short
Write-Host "  (review the above: no keys, no build artifacts, no venvs)"

# --- verdict --------------------------------------------------------------
Write-Host ""
if ($failures.Count -gt 0) {
    Write-Host "NOT READY - $($failures.Count) check(s) failed:" -ForegroundColor Red
    $failures | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Fix these before tagging. Nothing has been changed." -ForegroundColor Red
    exit 1
}

Write-Host "ALL CHECKS PASSED - version $pyproject" -ForegroundColor Green
Write-Host ""
Write-Host "The irreversible steps follow. Run them one at a time, PowerShell syntax:"
Write-Host ""
Write-Host "  git add -A"
Write-Host "  git commit -m `"Release v$pyproject - genesis authentication`""
Write-Host "  git tag v$pyproject-genesis-authentication"
Write-Host "  git push origin main --tags"
Write-Host ""
Write-Host "  python -m build"
Write-Host "  python -m twine upload dist/*"
Write-Host ""
Write-Host "Then: mint a fresh Zenodo DOI, and add a note to the v1.7.1 release"
Write-Host "pointing at v$pyproject and why anyone on 1.7.1 should move."
