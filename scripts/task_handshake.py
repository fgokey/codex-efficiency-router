"""Pure one-time task handshake formatting. No task ledger and no host inference.

Caller supplies only actually observed loaded-version/hash values. This helper
cannot prove that a model loaded anything and is not invoked on every turn.
"""
from __future__ import annotations
import re


def handshake(*, already_reported=False, loaded_version=None, loaded_policy_hash=None,
              mode='UNKNOWN', guard_status=None):
    if already_reported:
        return None
    if mode not in ('auto', 'fixed', 'adaptive', 'UNKNOWN'):
        raise ValueError('invalid routing mode')
    if not isinstance(loaded_version, str) or not re.fullmatch(r'\d+\.\d+\.\d+(?:-[\w.-]+)?', loaded_version):
        loaded_version = 'UNKNOWN'
    policy = loaded_policy_hash[:12] if isinstance(loaded_policy_hash, str) and re.fullmatch(r'[0-9a-f]{64}', loaded_policy_hash) else 'UNKNOWN'
    guard = 'policy-only'
    if guard_status and guard_status.get('registration') == 'PRESENT':
        guard = 'guarded'
        if (guard_status.get('live_verification') == 'PASS'
                and guard_status.get('evidence_basis') == 'operator-witnessed-native'
                and guard_status.get('review_attestation') == 'CURRENT_HASH_REVIEWED'):
            guard = 'live-verified'
    return f'CER v{loaded_version} | {mode} | guard={guard} | policy={policy}'
