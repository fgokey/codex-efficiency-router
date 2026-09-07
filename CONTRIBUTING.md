# Contributing

Contributions are welcome when they improve routing quality, compatibility, installation safety, measured efficiency, or documentation clarity.

## Principles

1. **Quality is a hard constraint.** Do not optimize token count or latency by silently accepting lower correctness.
2. **Evidence beats intuition.** Performance claims must describe task corpus, model/effort, success criteria, token metric, timing method, and repetitions.
3. **Keep routing cheap.** New runtime bookkeeping must justify its own token and latency cost.
4. **One agent by default.** Parallelism is added only for independent, bounded work with clear net benefit.
5. **No speculative model claims.** Verify model identifiers and supported reasoning efforts against current OpenAI documentation.

## Development

Requirements: Python 3.11+; runtime scripts use the standard library only.

```bash
python -m unittest discover -s tests -v
python scripts/doctor.py --source-tree .
```

## Pull requests

A PR should include:

- problem statement;
- behavioral change;
- tests or regression cases;
- compatibility impact;
- token/latency impact if relevant;
- documentation updates when behavior changes.

Avoid unrelated formatting or broad rewrites in the same PR.
