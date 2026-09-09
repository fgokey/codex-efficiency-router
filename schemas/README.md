# Manifest schema provenance

`plugin.schema.json` is the Agent Plugins 1.0.0 manifest schema retrieved through
web inspection on 2026-09-09 from
https://agent-plugins.org/schemas/1.0.0/plugin.schema.json (JSON reflowed, values retained).
The portable OpenAI manifest entry point and OpenAI extension are documented at
https://developers.openai.com/plugins/build/plugins .

OpenAI hook semantics are separately checked by `scripts/release_package.py`.
Passing this schema does not prove native discovery, role registration, trust or
runtime interception. No schemas are fetched at install or ordinary runtime.
