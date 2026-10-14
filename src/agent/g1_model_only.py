"""Gate G1 — model-only probe against the private Foundry Responses endpoint.

Confirms inference works independently of the MCP tool. Run:

    pip install -r requirements.txt
    $env:FOUNDRY_PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
    $env:MODEL_DEPLOYMENT_NAME    = "gpt-4o"
    python g1_model_only.py
"""
from __future__ import annotations

import os
import sys

from imanage_agent import build_client

MODEL = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o")

client = build_client()
response = client.responses.create(
    model=MODEL,
    instructions="You are a terse assistant. Answer in one short sentence.",
    input="Say hello and name the model family you run on.",
)

print(f"status={getattr(response, 'status', 'unknown')}")
print(f"[assistant] {response.output_text}")

sys.exit(0 if response.output_text else 1)
