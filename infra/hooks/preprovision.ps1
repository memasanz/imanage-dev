# Preprovision guard — validates Sprint 1 BYO inputs before deployment.
# Foundry (project + model) and APIM are brought by the customer via azd env / .env.

$ErrorActionPreference = 'Stop'

$required = @(
    'FOUNDRY_PROJECT_ENDPOINT',
    'APIM_SERVICE_NAME',
    'APIM_RESOURCE_GROUP_NAME',
    'APIM_GATEWAY_URL'
)

$missing = @()
foreach ($name in $required) {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name))) {
        $missing += $name
    }
}

if ($missing.Count -gt 0) {
    Write-Error "Missing BYO settings: $($missing -join ', '). Set them with: azd env set <NAME> <value> (see .env.example)."
    exit 1
}

$mode = if ([string]::IsNullOrWhiteSpace($env:IMANAGE_BACKEND_MODE)) { 'mock' } else { $env:IMANAGE_BACKEND_MODE }
Write-Host "BYO Foundry: $($env:FOUNDRY_PROJECT_ENDPOINT)"
Write-Host "BYO APIM:    $($env:APIM_SERVICE_NAME) ($($env:APIM_RESOURCE_GROUP_NAME))"
Write-Host "Backend mode: $mode"
