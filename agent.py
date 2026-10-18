"""tau2-bench agent: the stock LLMAgent plus guard.check() on every proposed tool call."""
from tau2.agent.llm_agent import LLMAgent
from tau2.data_model.message import AssistantMessage, SystemMessage
from tau2.utils.llm_utils import generate
import guard

MAX_RETRIES = 2

class AOPGuardAgent(LLMAgent):
    def _generate_next_message(self, message, state):
        msg = super()._generate_next_message(message, state)         # appends the incoming message, returns a proposal
        for _ in range(MAX_RETRIES):
            hit = guard.check(msg, state.messages)
            if not hit: return msg
            rule, reason = hit; guard._count(rule)
            note = SystemMessage(role="system", content=f"A code check blocked your last proposed action before it ran: {reason} "
                                                        "Do not repeat it. Fix the problem first, then continue.")
            msg = generate(model=self.llm, tools=self.tools, messages=state.system_messages + state.messages + [note],
                           call_name="agent_response", **self.llm_args)
        hit = guard.check(msg, state.messages)
        if not hit: return msg
        guard._count(hit[0] + "_fallback")
        return AssistantMessage(role="assistant", content=guard.FALLBACK[hit[0]])

def create_aop_guard_agent(tools, domain_policy, **kwargs):
    return AOPGuardAgent(tools=tools, domain_policy=domain_policy, llm=kwargs.get("llm"), llm_args=kwargs.get("llm_args"))
