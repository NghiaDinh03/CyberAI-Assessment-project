# capture_3_real_ui.ps1
param(
    [string]$outDir = "evidence_final_v4"
)

# Start Chrome headless with remote debugging
$proc = Start-Process -FilePath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList @(
    '--headless=new',
    '--remote-debugging-port=9222',
    '--user-data-dir=C:\temp\cdp_prof_real',
    '--window-size=1600,1050',
    '--disable-gpu',
    'about:blank'
) -PassThru

Start-Sleep -Seconds 2

try {
    # Open new tab for login
    $tab = Invoke-RestMethod -Method PUT -Uri 'http://127.0.0.1:9222/json/new?http://localhost:3081/login'
    $wsUrl = $tab.webSocketDebuggerUrl
    Write-Host "Connected: $wsUrl"

    $ws = [System.Net.WebSockets.ClientWebSocket]::new()
    $cts = [System.Threading.CancellationTokenSource]::new(60000)
    $ws.ConnectAsync([System.Uri]::new($wsUrl), $cts.Token).Wait()

    $script:msgId = 0
    function Send-CDP($method, $params = @{}) {
        $script:msgId = ($script:msgId + 1)
        $payload = @{ id = $script:msgId; method = $method; params = $params } | ConvertTo-Json -Compress -Depth 10
        $sendBytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
        $ws.SendAsync([System.ArraySegment[byte]]::new($sendBytes), [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $cts.Token).Wait()

        $allBytes = [System.Collections.Generic.List[byte]]::new()
        $buffer = [byte[]]::new(65536)
        while ($true) {
            $res = $ws.ReceiveAsync([System.ArraySegment[byte]]::new($buffer), $cts.Token).Result
            for ($i = 0; $i -lt $res.Count; $i++) { $allBytes.Add($buffer[$i]) }
            if ($res.EndOfMessage) {
                $text = [System.Text.Encoding]::UTF8.GetString($allBytes.ToArray())
                try {
                    $json = $text | ConvertFrom-Json
                    if ($json.id -eq $script:msgId) { return $json }
                } catch {}
                $allBytes.Clear()
            }
        }
    }

    function Eval-JS($expr) {
        $r = Send-CDP "Runtime.evaluate" @{ expression = $expr; returnByValue = $true; awaitPromise = $true }
        return $r.result.result.value
    }

    function Take-Shot($filename) {
        $shot = Send-CDP "Page.captureScreenshot" @{ format = "png" }
        if ($shot.result.data) {
            $bytes = [System.Convert]::FromBase64String($shot.result.data)
            $targetPath = Join-Path (Get-Location) (Join-Path $outDir $filename)
            [System.IO.File]::WriteAllBytes($targetPath, $bytes)
            Write-Host "[OK] Saved screenshot: $filename ($($bytes.Length) bytes)"
        }
    }

    Send-CDP "Page.enable" | Out-Null
    Send-CDP "Runtime.enable" | Out-Null
    Start-Sleep -Seconds 2

    # Set auth in localStorage
    Write-Host "Setting authentication tokens..."
    $authScript = @"
        localStorage.setItem('cyberai_auth_token', 'eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiZDZmZmMwMzciLCAidXNlcm5hbWUiOiAiYWRtaW4iLCAicm9sZSI6ICJhZG1pbiIsICJleHAiOiAxNzkwNTkyMDg5LjYxNDcxMn0.a6e9bb28b3042b5181a5b53398710fc7a4c7e94f29b156c117dc77e0d07a86ae');
        localStorage.setItem('cyberai_auth_user', JSON.stringify({
            id: 'd6ffc037',
            username: 'admin',
            email: 'admin@cyberai.vn',
            full_name: 'CyberAI Administrator',
            role: 'admin'
        }));
        localStorage.setItem('cyberai_theme', 'dark');
        localStorage.setItem('cyberai_lang', 'vi');
        localStorage.setItem('language', 'vi');
"@
    Eval-JS $authScript | Out-Null

    # ─────────────────────────────────────────────────────────────
    # 1. TEMPLATE PREVIEW SCREENSHOT
    # ─────────────────────────────────────────────────────────────
    Write-Host "Preparing Template Preview..."
    $templateInit = @"
        localStorage.setItem('reuse_iso_form', JSON.stringify({
            template_id: 'iso27001_enterprise_sample',
            template_name: 'Doanh nghi\u1ec7p Ti\u00eau chu\u1ea9n ISO 27001',
            organization: { name: 'C\u00f4ng ty C\u1ed5 ph\u1ea7n C\u00f4ng ngh\u1ec7 M\u1eabu Vi\u1ec7t Nam (Template Data)', field: 'Fintech / Banking' },
            assessment_standard: 'iso27001',
            implemented_controls: ['A.5.1', 'A.5.2', 'A.5.3', 'A.8.1', 'A.8.2']
        }));
        window.location.href = 'http://localhost:3081/form-iso';
"@
    Eval-JS $templateInit | Out-Null
    Start-Sleep -Seconds 3

    # Click Next for Step 1
    $clickNext = @"
        (function() {
            const btns = Array.from(document.querySelectorAll('button'));
            const nxt = btns.find(b => b.textContent.includes('Ti\u1ebfp t\u1ee5c') || b.textContent.includes('Next'));
            if (nxt) { nxt.click(); return 'clicked next'; }
            return 'not found';
        })();
"@
    $r1 = Eval-JS $clickNext
    Start-Sleep -Seconds 2

    # Click Next for Step 2
    $r2 = Eval-JS $clickNext
    Start-Sleep -Seconds 2

    Take-Shot "ui_screenshot_template.png"

    # ─────────────────────────────────────────────────────────────
    # 2. ZERO-VERIFIED ASSESSMENT RESULT SCREENSHOT
    # ─────────────────────────────────────────────────────────────
    Write-Host "Preparing Zero-Verified Result..."
    $navHistory = @"
        (function() {
            const btns = Array.from(document.querySelectorAll('button'));
            const hist = btns.find(b => b.textContent.includes('L\u1ecbch s\u1eed') || b.textContent.includes('History'));
            if (hist) { hist.click(); return 'nav history'; }
            return 'history tab not found';
        })();
"@
    $hRes = Eval-JS $navHistory
    Write-Host "Nav History: $hRes"
    Start-Sleep -Seconds 2

    # Click "Xem kết quả" for asm_zero_verified_2026
    $clickZero = @"
        (function() {
            const items = Array.from(document.querySelectorAll('div[class*="historyItem"]'));
            const zeroItem = items.find(it => it.textContent.includes('T\u1ef1 K\u00ea Khai') || it.textContent.includes('asm_zero'));
            if (zeroItem) {
                const viewBtn = zeroItem.querySelector('button');
                if (viewBtn) { viewBtn.click(); return 'clicked zeroItem'; }
            }
            return 'zeroItem not found (items=' + items.length + ')';
        })();
"@
    $resZero = Eval-JS $clickZero
    Write-Host "Click Zero Result: $resZero"
    Start-Sleep -Seconds 3

    Take-Shot "ui_screenshot_zero_verified.png"

    # ─────────────────────────────────────────────────────────────
    # 3. UPLOADED EVIDENCE + MANIFEST + MAPPING CONTROLS SCREENSHOT
    # ─────────────────────────────────────────────────────────────
    Write-Host "Preparing Uploaded Evidence + Manifest..."
    # Switch back to History tab
    Eval-JS $navHistory | Out-Null
    Start-Sleep -Seconds 2

    # Click "Xem kết quả" for asm_iso_normal_2026
    $clickIso = @"
        (function() {
            const items = Array.from(document.querySelectorAll('div[class*="historyItem"]'));
            const isoItem = items.find(it => it.textContent.includes('Qu\u1ed1c gia') || it.textContent.includes('asm_iso_'));
            if (isoItem) {
                const viewBtn = isoItem.querySelector('button');
                if (viewBtn) { viewBtn.click(); return 'clicked isoItem'; }
            }
            return 'isoItem not found';
        })();
"@
    $resIso = Eval-JS $clickIso
    Write-Host "Click ISO Result: $resIso"
    Start-Sleep -Seconds 3

    # Now click "Luồng kiểm chứng (Audit Trace)" button
    $clickAuditTrace = @"
        (function() {
            const btns = Array.from(document.querySelectorAll('button'));
            const traceBtn = btns.find(b => b.textContent.includes('Lu\u1ed3ng ki\u1ec3m ch\u1ee9ng') || b.textContent.includes('Audit Trace'));
            if (traceBtn) { traceBtn.click(); return 'clicked traceBtn'; }
            return 'traceBtn not found';
        })();
"@
    $resTrace = Eval-JS $clickAuditTrace
    Write-Host "Click Audit Trace Result: $resTrace"
    Start-Sleep -Seconds 3

    # Scroll inner container so evidence_parsed, manifest_id and control mapping are clearly visible
    $scrollModal = @"
        (function() {
            const pre = Array.from(document.querySelectorAll('pre')).find(p => p.textContent.includes('evidence_manifest_id') || p.textContent.includes('control_mapping'));
            if (pre) {
                pre.scrollIntoView({ block: 'center' });
                return 'scrolled pre into view';
            }
            const containers = Array.from(document.querySelectorAll('div'));
            const scrollBox = containers.find(c => c.style && c.style.maxHeight && c.style.overflowY);
            if (scrollBox) {
                scrollBox.scrollTop = 320;
                return 'scrolled container';
            }
            return 'no scrollBox found';
        })();
"@
    $sRes = Eval-JS $scrollModal
    Write-Host "Scroll result: $sRes"
    Start-Sleep -Seconds 1

    Take-Shot "ui_screenshot_manifest.png"

    $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "done", $cts.Token).Wait()
} finally {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
}
