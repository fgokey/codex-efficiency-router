# Token and Latency Efficiency

## What actually saves tokens

The project targets structural waste rather than merely selecting the cheapest model:

- avoid an extra LLM call just to route;
- avoid feeding the full root conversation to every worker;
- stop high-end reasoning once the decision is frozen;
- pass compact contracts instead of transcripts;
- prefer direct tool concurrency before model concurrency;
- avoid duplicate agents discovering the same facts;
- avoid repeated successful verification;
- escalate before a weak model enters a long brute-force loop.

## What can increase tokens

- spawning many agents for a small task;
- using a planner, router, executor, reviewer, and integrator for work one agent could finish;
- asking multiple models to independently solve the same problem;
- keeping Astra as the root for long deterministic follow-up work;
- using `xhigh`/`max` by default;
- copying full logs and full exploration history into every handoff.

## Speed strategy

Fastest safe ordering:

1. parallelize independent I/O/tool calls;
2. use a faster sufficient model for bounded work;
3. parallelize independent reasoning work only when startup/context/merge overhead is smaller than the expected wall-clock saving;
4. keep dependent reasoning sequential.

## Quality constraint

Efficiency claims are invalid if they increase retries, escaped defects, or manual repair. Measure the whole task, not only the successful final attempt.

A useful comparison records:

- success/failure against the same acceptance criteria;
- total tokens across all agents and retries;
- elapsed time;
- number of model invocations/agents;
- number of failed loops;
- human intervention required.
