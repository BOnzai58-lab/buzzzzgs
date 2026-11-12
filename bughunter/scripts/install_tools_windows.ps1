# BugHunter AI — Security Tools Installer for Windows
# Run as Administrator in PowerShell

Write-Host "Installing BugHunter AI security tools..." -ForegroundColor Cyan

# Check Go
if (-not (Get-Command go -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Go..." -ForegroundColor Yellow
    winget install GoLang.Go
    $env:Path += ";C:\Program Files\Go\bin;$env:USERPROFILE\go\bin"
}

# Install Go-based tools
$tools = @(
    "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
    "github.com/projectdiscovery/dnsx/cmd/dnsx@latest",
    "github.com/projectdiscovery/httpx/cmd/httpx@latest",
    "github.com/projectdiscovery/katana/cmd/katana@latest",
    "github.com/projectdiscovery/naabu/v2/cmd/naabu@latest",
    "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
    "github.com/lc/gau/v2/cmd/gau@latest",
    "github.com/tomnomnom/waybackurls@latest"
)

foreach ($tool in $tools) {
    $name = ($tool -split "/")[-1] -replace "@latest",""
    Write-Host "Installing $name..." -ForegroundColor Yellow
    go install -v $tool
    if ($LASTEXITCODE -eq 0) {
        Write-Host "$name installed OK" -ForegroundColor Green
    } else {
        Write-Host "$name FAILED" -ForegroundColor Red
    }
}

# Update Nuclei templates
if (Get-Command nuclei -ErrorAction SilentlyContinue) {
    Write-Host "Updating Nuclei templates..." -ForegroundColor Yellow
    nuclei -update-templates
}

Write-Host "`nAll tools installed. Run 'nuclei -update-templates' periodically." -ForegroundColor Green
Write-Host "Note: SQLMap and Dalfox require Python. Install separately if needed." -ForegroundColor Yellow

