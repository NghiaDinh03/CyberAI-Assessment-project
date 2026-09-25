# Compute SHA-256 for final_changes.patch and the 23 evidence files
$utf8NoBom = New-Object System.Text.UTF8Encoding $false

# 1. Update final_changes.patch.sha256
$patchHash = (Get-FileHash evidence\final_changes.patch -Algorithm SHA256).Hash.ToLower()
[System.IO.File]::WriteAllText((Join-Path (Get-Location) "evidence\final_changes.patch.sha256"), "$patchHash  final_changes.patch`n", $utf8NoBom)

# 2. List the 23 files to include in manifest_sha256.txt
$targetFiles = @(
    "AUDIT_REPORT.md",
    "backend_audit_tests.log",
    "backend_full_tests.log",
    "env_reproduction.log",
    "final_changes.patch",
    "final_changes.patch.sha256",
    "frontend_tests.log",
    "functional_matrix.log",
    "git_state.txt",
    "test_results.log",
    "ui_screenshot.png",
    "iso_assessment/assessment.json",
    "iso_assessment/audit_trace.json",
    "iso_assessment/report.docx",
    "iso_assessment/report.pdf",
    "iso_assessment/Risk_Register.xlsx",
    "iso_assessment/run.log",
    "iso_assessment/SoA.xlsx",
    "tcvn_assessment/assessment.json",
    "tcvn_assessment/report.docx",
    "tcvn_assessment/report.pdf",
    "tcvn_assessment/run.log",
    "tcvn_assessment/SoA.xlsx"
)

$lines = foreach ($rel in $targetFiles) {
    $fullPath = Join-Path (Get-Location) ("evidence\" + $rel.Replace('/', '\'))
    if (-not (Test-Path $fullPath)) {
        throw "Missing expected file: $fullPath"
    }
    $h = (Get-FileHash $fullPath -Algorithm SHA256).Hash.ToLower()
    "$h  $rel"
}

$content = ($lines -join "`n") + "`n"
[System.IO.File]::WriteAllText((Join-Path (Get-Location) "evidence\manifest_sha256.txt"), $content, $utf8NoBom)

Write-Host "Manifest generated successfully with $($lines.Count) files (UTF-8 no BOM LF)."

