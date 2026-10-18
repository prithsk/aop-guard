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
_Run it to populate._
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
