"""Run tau2-bench retail twice, stock agent vs AOP guard, same model and simulated user, and report
tau2's own pass^k.

  python run.py --num-tasks 40 --num-trials 4          # needs OPENAI_API_KEY in .env
"""
import argparse, json, datetime as dt
from common import ROOT, need, os

def main(a):
    need("OPENAI_API_KEY")
    from tau2.registry import registry
    from tau2.run import run_domain
    from tau2.data_model.simulation import TextRunConfig
    from tau2.metrics.agent_metrics import compute_metrics
    import agent, guard
    registry.register_agent_factory(agent.create_aop_guard_agent, "aop_guard")
    out = {}; (ROOT / "results").mkdir(exist_ok=True)
    for name in ("llm_agent", "aop_guard"):
        cfg = TextRunConfig(domain=a.domain, agent=name, llm_agent=a.model, llm_user=a.user_model, num_trials=a.num_trials,
                            num_tasks=a.num_tasks, max_concurrency=a.concurrency, seed=a.seed,
                            save_to=str(ROOT / "results" / f"{a.domain}-{name}-{dt.date.today()}"))
        m = compute_metrics(run_domain(cfg)); out[name] = m
        print(f"  {name}: avg reward {m.avg_reward:.3f}, pass^k {m.pass_hat_ks}", flush=True)
    b, g = out["llm_agent"], out["aop_guard"]; ks = sorted(b.pass_hat_ks)
    md = [f"# Policy checks in code on tau2-bench {a.domain}, {dt.date.today()}", "",
          f"{a.num_tasks} tasks, {a.num_trials} trials each. Agent `{a.model}`, simulated user `{a.user_model}`. "
          "Same prompt, tools and user for both; the only difference is the code checks.", "",
          "| Metric | Stock LLM agent | + policy checks in code | Change |", "|---|---|---|---|",
          f"| Average reward | {b.avg_reward:.3f} | {g.avg_reward:.3f} | {g.avg_reward - b.avg_reward:+.3f} |"]
    md += [f"| pass^{k} | {b.pass_hat_ks[k]:.3f} | {g.pass_hat_ks[k]:.3f} | {g.pass_hat_ks[k] - b.pass_hat_ks[k]:+.3f} |" for k in ks]
    md += [f"| Agent cost per task | ${b.avg_agent_cost:.4f} | ${g.avg_agent_cost:.4f} | |", "",
           "Blocks by rule: " + (", ".join(f"{k} {v}" for k, v in guard.STATS.most_common()) or "none"), "",
           "## Honest limits", "",
           "- Simulated customers, not real ones. tau2-bench's user simulator is an LLM and makes its own mistakes.",
           "- Five rules, written from the retail policy text. Decagon's production checks are surely broader; this tests the principle, not their product.",
           f"- {a.num_tasks} tasks. pass^k with k up to {a.num_trials} shows reliability, but small task counts make the last digit noisy."]
    s = "\n".join(md); (ROOT / "results" / f"{a.domain}-{dt.date.today()}.md").write_text(s, encoding="utf-8"); print(s)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--domain", default="retail"); ap.add_argument("--num-tasks", type=int, default=40)
    ap.add_argument("--num-trials", type=int, default=4); ap.add_argument("--model", default="gpt-4.1-mini")
    ap.add_argument("--user-model", default="gpt-4.1-mini"); ap.add_argument("--concurrency", type=int, default=6); ap.add_argument("--seed", type=int, default=300)
    main(ap.parse_args())
