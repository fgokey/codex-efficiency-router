# Compatibility

Last documentation verification: **2026-09-07**.

## Expected model identifiers

- `gpt-6-astra`
- `gpt-5.6-sol`
- `gpt-5.6-terra`
- `gpt-5.6-luna`

The project uses Astra `high` and GPT-5.6 `medium` presets. Current OpenAI documentation lists Astra reasoning efforts `low`, `medium`, `high`, `xhigh`, and `max`; GPT-5.6 Sol/Terra/Luna support the documented GPT-5.6 reasoning range.

## Codex features used

- local Skills;
- custom agents;
- per-agent `model`;
- per-agent `model_reasoning_effort`;
- optional multi-agent execution.

The installer does not require a third-party daemon, proxy, API key, or Python package.

## Source links

Current OpenAI references used when preparing v0.1.0:

- https://developers.openai.com/api/docs/models/gpt-6-astra
- https://developers.openai.com/api/docs/models/gpt-5.6-sol
- https://developers.openai.com/api/docs/models/gpt-5.6-terra
- https://developers.openai.com/api/docs/models/gpt-5.6-luna
- https://learn.chatgpt.com/zh-Hans/docs/agent-configuration/subagents
- https://learn.chatgpt.com/zh-Hans/docs/build-skills

Codex and model catalogs change quickly. Verify these references before changing compatibility claims.
