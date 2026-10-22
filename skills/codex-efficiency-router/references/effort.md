# Select capability once per work unit

|Role|Model/effort|
|---|---|
|`luna_worker`|gpt-6-luna/high|
|`terra_executor`|gpt-5.6-terra/medium|
|`sol61_engineer`|gpt-6.1-sol/high|
|`sol_engineer`|gpt-6.1-sol/medium (compatibility name only)|
|`astra_architect`|gpt-6-astra/high|

Sol means GPT-6.1 Sol only. New Sol routes use `cer_auto_sol61_engineer`; never select gpt-6-sol or gpt-5.6-sol, including explicit pins, fallback or owner reuse. The old role filename is an upgrade alias bound to 6.1, not another model. Retired-model requests fail rather than being silently remapped.

Choose model and effort jointly. Use `cer_auto_<role>` with explicit effort and `fork_turns=none`; fixed fallback requires observed unavailability and the exact role/catalog pair. Never silently remap. Verify actual host binding before RELEASE; requested parameters are not identity. Respect supported explicit pins and model/effort ceilings.

Default engineering or review uses Sol61/high when difficulty is unknown. Confirmed simple work may use medium; bounded Terra and mechanical Luna work require low risk and strong checks. Low remains opt-in for deterministic Luna tasks. Higher effort needs a demonstrated reasoning bottleneck, supported effort and expected benefit, not build duration or a retry count. Ultra additionally needs one authorized Sol/Astra coordinator and independent disjoint units; it grants no permission.

Same-configuration delegation needs contextual value AND net benefit. Prefer one implementation owner plus an independent reviewer only when useful. Two writers max; never one agent per file. At meaningful changes check ready work, dependencies and ownership; parallelize only independent units without shared write/build state.

Resolve MISMATCH at a safe boundary, reconcile effects and review affected acceptance. UNKNOWN is not proof of mismatch, but neither permits unverified writes. Both suspend automatic low; later VERIFIED does not erase outstanding review. Keep attempts and user limits. Missing requirements, authority, environment or observations need repair, not escalation. No repeated model probes or compulsory tier ladder.
