"""Code-level checks on proposed tool calls, the way Decagon describes AOPs: sensitive validation runs in
code, not at the model's discretion. Rules come straight from tau2-bench's retail policy text."""
import json, re, threading, collections

WRITES = {"cancel_pending_order", "exchange_delivered_order_items", "modify_pending_order_address",
          "modify_pending_order_items", "modify_pending_order_payment", "modify_user_address", "return_delivered_order_items"}
NEEDS_PENDING = {"cancel_pending_order", "modify_pending_order_address", "modify_pending_order_items", "modify_pending_order_payment"}
NEEDS_DELIVERED = {"exchange_delivered_order_items", "return_delivered_order_items"}
ONCE = {"exchange_delivered_order_items", "modify_pending_order_items"}
AUTH = {"find_user_id_by_email", "find_user_id_by_name_zip"}
YES = re.compile(r"\b(yes|yeah|yep|yup|confirm(ed)?|go ahead|proceed|please do|do it|sure|correct|that'?s right|sounds good)\b", re.I)
NO = re.compile(r"^\s*no\b|\bdon'?t\b|\bdo not\b|\bwait\b|\bhold on\b|\bnot yet\b", re.I)

STATS = collections.Counter(); _lock = threading.Lock()
def _count(rule):
    with _lock: STATS[rule] += 1

def _role(m): return getattr(m, "role", None)

def _calls(history):
    """id -> (name, arguments) for every tool call the agent made."""
    out = {}
    for m in history:
        for c in (getattr(m, "tool_calls", None) or []) if _role(m) == "assistant" else []:
            out[c.id] = (c.name, c.arguments or {})
    return out

def _results(history):
    calls = _calls(history); res = []
    for m in history:
        if _role(m) == "tool" and m.id in calls:
            ok = not getattr(m, "error", False) and not (m.content or "").strip().lower().startswith("error")
            res.append((calls[m.id][0], calls[m.id][1], m.content or "", ok))
    return res

def _order_status(results, order_id):
    status = None
    for name, args, content, ok in results:
        if ok and name == "get_order_details" and args.get("order_id") == order_id:
            try: status = json.loads(content).get("status")
            except Exception: m = re.search(r'"status"\s*:\s*"([^"]+)"', content); status = m.group(1) if m else status
    return status

def check(msg, history):
    """Return (rule, reason) if the proposed message breaks a policy rule, else None."""
    calls = getattr(msg, "tool_calls", None) or []
    if len(calls) > 1: return "one_call", "The policy allows at most one tool call at a time."
    if not calls or calls[0].name not in WRITES: return None
    c = calls[0]; results = _results(history); oid = (c.arguments or {}).get("order_id")
    if not any(ok and n in AUTH for n, _, _, ok in results):
        return "auth", "The user has not been authenticated. Locate their user id by email, or by name and zip code, first."
    last_user = next((m for m in reversed(history) if _role(m) == "user" and (m.content or "").strip()), None)
    if last_user is None or not YES.search(last_user.content) or NO.search(last_user.content):
        return "confirm", "Database changes need explicit confirmation. List the exact action details and ask the user to reply yes."
    if oid and c.name in NEEDS_PENDING | NEEDS_DELIVERED:
        st = _order_status(results, oid)
        if st is None: return "status_unknown", f"Check the status of order {oid} with get_order_details before acting on it."
        need = "pending" if c.name in NEEDS_PENDING else "delivered"
        if st != need: return "status", f"Order {oid} is '{st}'. {c.name} only applies to {need} orders."
    if oid and c.name in ONCE and any(ok and n in ONCE and a.get("order_id") == oid for n, a, _, ok in results):
        return "once", f"Exchange or modify-items can only be called once per order, and order {oid} was already changed."
    return None

FALLBACK = {
    "auth": "Before I can make any changes, I need to verify your identity. Could you share your email, or your name and zip code?",
    "confirm": "Before I make that change, please confirm the details I listed are correct. Reply yes to proceed.",
    "status_unknown": "Let me check the current status of that order before making any change.",
    "status": "That order isn't in a state where I can make that change. Is there something else I can help with on it?",
    "once": "That order has already been changed once, and the policy doesn't allow a second change of that kind.",
    "one_call": "Let me take this one step at a time.",
}
