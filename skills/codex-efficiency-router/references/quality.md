# Evidence and recovery

Contract: requirement | current check/review | applicable state | PASS/FAIL/UNKNOWN. Design may need reasoned review, not builds. Required integration/review cannot be waived; optional risks may coexist with PASS. Authorized scope changes retain earlier gaps; dependencies and dirty state affect evidence freshness.

Checkpoint fields: contracts/state, valid completed scopes, active workers, failed methods/pairs and remaining budget. Update on transitions; no secrets or overwriting another task. Reconstruct unknown history before replay. Error/contract renaming also never renews retries; justified extensions retain history. Offline helpers prove neither live enforcement nor quality.
