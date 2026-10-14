#!/bin/sh
# Builds the React/Vite SPA and stages it into the backend so the App Service image serves
# it at /ui. Runs before `azd package`/deploy.
set -e
root="$(cd "$(dirname "$0")/../.." && pwd)"
frontend="$root/src/frontend"
ui_target="$root/src/backend/ui"

echo "Building SPA in $frontend ..."
cd "$frontend"
if [ ! -d node_modules ]; then
  npm install --no-audit --no-fund
fi
npm run build

rm -rf "$ui_target"
mkdir -p "$ui_target"
cp -R "$frontend/dist/." "$ui_target/"
echo "SPA staged into $ui_target"
