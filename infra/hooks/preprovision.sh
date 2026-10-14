#!/bin/sh
# Preprovision guard — validates Sprint 1 BYO inputs before deployment.
# Foundry (project + model) and APIM are brought by the customer via azd env / .env.
set -e

missing=""
for name in FOUNDRY_PROJECT_ENDPOINT APIM_SERVICE_NAME APIM_RESOURCE_GROUP_NAME APIM_GATEWAY_URL; do
  eval "val=\${$name:-}"
  if [ -z "$val" ]; then
    missing="$missing $name"
  fi
done

if [ -n "$missing" ]; then
  echo "Missing BYO settings:$missing. Set them with: azd env set <NAME> <value> (see .env.example)." >&2
  exit 1
fi

echo "BYO Foundry: $FOUNDRY_PROJECT_ENDPOINT"
echo "BYO APIM:    $APIM_SERVICE_NAME ($APIM_RESOURCE_GROUP_NAME)"
echo "Backend mode: ${IMANAGE_BACKEND_MODE:-mock}"
