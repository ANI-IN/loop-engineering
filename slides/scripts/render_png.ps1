<#
Renders every slide of a deck to PNG at 1280x720 with PowerPoint, for a visual fit review.

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File slides/scripts/render_png.ps1 `
        -Deck slides/build/sample.pptx -OutDir slides/build/png

Opens the deck read-only through PowerPoint automation, exports slide N to
<OutDir>/slide-NN.png, and always closes the deck and quits PowerPoint, also on error.
The output folder is generated and never committed.
#>
param(
    [Parameter(Mandatory = $true)][string]$Deck,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [int]$Width = 1280,
    [int]$Height = 720
)

$ErrorActionPreference = "Stop"
$deckPath = (Resolve-Path -LiteralPath $Deck).Path
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$outPath = (Resolve-Path -LiteralPath $OutDir).Path

$app = $null
$presentation = $null
try {
    $app = New-Object -ComObject PowerPoint.Application
    # Open(FileName, ReadOnly, Untitled, WithWindow): read-only, no window.
    $presentation = $app.Presentations.Open($deckPath, -1, 0, 0)
    $count = $presentation.Slides.Count
    for ($i = 1; $i -le $count; $i++) {
        $file = Join-Path $outPath ("slide-{0:D2}.png" -f $i)
        $presentation.Slides.Item($i).Export($file, "PNG", $Width, $Height)
        Write-Output $file
    }
}
finally {
    if ($null -ne $presentation) {
        $presentation.Close()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($presentation)
    }
    if ($null -ne $app) {
        $app.Quit()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app)
    }
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}
