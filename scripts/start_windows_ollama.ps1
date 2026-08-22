# Script khởi chạy Ollama Windows với cấu hình AMD iGPU và Port 11434
$env:OLLAMA_IGPU_ENABLE = "1"
$env:OLLAMA_HOST = "0.0.0.0:11434"
[System.Environment]::SetEnvironmentVariable("OLLAMA_IGPU_ENABLE", "1", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "User")

Write-Host "Stopping existing Ollama processes..."
Get-Process -Name *ollama* -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
if (-not (Test-Path $ollamaExe)) {
    $ollamaCmd = Get-Command ollama.exe -ErrorAction SilentlyContinue
    if ($ollamaCmd) {
        $ollamaExe = $ollamaCmd.Source
    }
}

Write-Host "Starting Ollama server from $ollamaExe..."
Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden

Start-Sleep -Seconds 3

try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 5
    Write-Host "Ollama Windows is online! Models loaded:"
    $resp.models | Format-Table name, size, modified_at
} catch {
    Write-Error "Failed to connect to Ollama Windows: $_"
}
