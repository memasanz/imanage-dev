# Builds the React/Vite SPA and stages it into the backend so the App Service image serves
# it at /ui. Runs before `azd package`/deploy.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot | Split-Path -Parent
$frontend = Join-Path $root 'src/frontend'
$uiTarget = Join-Path $root 'src/backend/ui'

Write-Host "Building SPA in $frontend ..."
Push-Location $frontend
try {
  if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    npm install --no-audit --no-fund
  }
  npm run build
} finally {
  Pop-Location
}

if (Test-Path $uiTarget) { Remove-Item $uiTarget -Recurse -Force }
New-Item -ItemType Directory -Force -Path $uiTarget | Out-Null
Copy-Item -Path (Join-Path $frontend 'dist/*') -Destination $uiTarget -Recurse -Force
Write-Host "SPA staged into $uiTarget"
