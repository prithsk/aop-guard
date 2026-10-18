# aop-guard

Does moving an agent's policy rules from the prompt into code make it more reliable? Decagon builds its customer-service agents on Agent Operating Procedures, and describes the key design choice as running sensitive validation steps, like refund eligibility and identity checks, in code rather than at the model's discretion. This tests that principle on the open benchmark for customer-service agents, [tau2-bench](https://github.com/sierra-research/tau2-bench), retail domain.

Two runs, same model, same prompt, same tools, same simulated customer. The second adds five code checks that run before any database write, each taken word for word from tau2's retail policy:

| Rule | Policy text it enforces |
|---|---|
| auth | Authenticate the user by email, or name and zip, before anything else |
| confirm | List the action details and get explicit confirmation (yes) before any database change |
| status | Cancel or modify only pending orders; return or exchange only delivered ones |
| once | Exchange or modify-items can be called only once per order |
| one_call | At most one tool call at a time |

When a check blocks a call, the agent is told why and gets two more tries. If it still breaks the rule, it falls back to a safe message to the customer. Reads always pass through untouched. Scores are tau2-bench's own pass^k, computed by its own metrics code.

## Results

<!-- results:start -->
# Policy checks in code on tau2-bench retail, 2026-10-18

20 tasks, 4 trials each. Agent `gpt-4.1-mini`, simulated user `gpt-4.1-mini`. Same prompt, tools and user for both; the only difference is the code checks.

| Metric | Stock LLM agent | + policy checks in code | Change |
|---|---|---|---|
| Average reward | 0.425 | 0.438 | +0.013 |
| pass^1 | 0.425 | 0.438 | +0.013 |
| pass^2 | 0.250 | 0.333 | +0.083 |
| pass^3 | 0.163 | 0.287 | +0.125 |
| pass^4 | 0.100 | 0.250 | +0.150 |
| Agent cost per task | $0.0103 | $0.0110 | |

Blocks by rule: one_call 199, one_call_fallback 46, confirm 3, status 1

## Honest limits

- Simulated customers, not real ones. tau2-bench's user simulator is an LLM and makes its own mistakes.
- Five rules, written from the retail policy text. Decagon's production checks are surely broader; this tests the principle, not their product.
- 20 tasks. pass^k with k up to 4 shows reliability, but small task counts make the last digit noisy.- Most blocks came from the one-tool-call-at-a-time rule (199 blocks, 46 fallbacks). The confirmation and order-status checks fired 4 times in total, so the reliability gain comes mostly from forcing one action at a time.
- pass^4 of 0.10 vs 0.25 means 2 vs 5 of 20 tasks solved on all four tries. The gap grows at every k, but the exact values are noisy at this size.

<!-- results:end -->

## Run it

```
git clone https://github.com/sierra-research/tau2-bench ../tau2-bench
pip install -e ../tau2-bench
pip install websockets
cp .env.example .env      # OPENAI_API_KEY
python run.py --num-tasks 40 --num-trials 4
```

## License

MIT
