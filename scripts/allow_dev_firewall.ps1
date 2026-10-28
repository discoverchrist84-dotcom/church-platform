# Lets phones reach the dev server through the Windows firewall. Run ONCE, in PowerShell "as Administrator":
#     powershell -ExecutionPolicy Bypass -File scripts\allow_dev_firewall.ps1
# Hotspots are usually classed as "Public" networks, which Windows blocks by default, so the rule covers all profiles.
param([int]$Port = 8000)
$name = "Church dev server $Port"
if (-not (Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $name -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow -Profile Any | Out-Null
    Write-Host "Allowed inbound TCP $Port. Remove later with: Remove-NetFirewallRule -DisplayName '$name'"
} else {
    Write-Host "Rule already exists."
}
