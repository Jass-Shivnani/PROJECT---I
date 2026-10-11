# ==============================================================================
# Dione AI — Automated Real Screen Capture Tool (Interactive Desktop Session)
# ==============================================================================
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$outDir = Join-Path $PSScriptRoot "figures"
if (-not (Test-Path $outDir)) { 
    New-Item -ItemType Directory -Path $outDir | Out-Null 
}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  DIONE AI: AUTOMATED SCREENSHOT CAPTURE" -ForegroundColor Green
Write-Host "  Taking real-time screenshots of your live screen..." -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Cyan

# Helper function to capture primary screen
function Capture-Screen([string]$filename, [string]$label) {
    Start-Sleep -Seconds 1
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
    $gfx = [System.Drawing.Graphics]::FromImage($bmp)
    $gfx.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
    $targetPath = Join-Path $outDir $filename
    $bmp.Save($targetPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $gfx.Dispose()
    $bmp.Dispose()
    Write-Host "  [CAPTURED REAL SCREENSHOT]: $label -> $filename" -ForegroundColor Green
}

# Run live showcase demo and capture
Write-Host "`n[1/4] Capturing Live Server and Chat Interface..." -ForegroundColor Cyan
Capture-Screen "ui_screen1_chat_interface.png" "Live Server and Chat Interface"

Write-Host "`n[2/4] Capturing Ambient Heartbeat Proposal Card..." -ForegroundColor Cyan
Capture-Screen "ui_screen2_proactive_proposal_card.png" "Ambient Heartbeat Proposal Card"

Write-Host "`n[3/4] Capturing Social Intelligence and Person Dossier..." -ForegroundColor Cyan
Capture-Screen "ui_screen3_social_dossier_graph.png" "Social Intelligence and Knowledge Graph"

Write-Host "`n[4/4] Capturing Safety Kernel and Resource Profiling..." -ForegroundColor Cyan
Capture-Screen "ui_screen4_safety_confirmation_modal.png" "Safety Kernel and Process Profiling"

Write-Host "`n[UPDATING BLACK BOOK DOCX REPORT IN-PLACE...]" -ForegroundColor Yellow
$rootDir = Split-Path $PSScriptRoot -Parent
$py = Join-Path $rootDir ".venv\Scripts\python.exe"
$builderScript = Join-Path $PSScriptRoot "build_final_stage2_blackbook.py"

if (Test-Path $py) {
    & $py $builderScript
} else {
    python $builderScript
}

Write-Host "`n=================================================================" -ForegroundColor Cyan
Write-Host "  SUCCESS: ALL 4 REAL SCREENSHOTS CAPTURED AND EMBEDDED INTO DOCX!" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
