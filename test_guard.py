import json
from types import SimpleNamespace as N
import guard
def A(text=None, calls=()): return N(role="assistant", content=text, tool_calls=[N(id=c[0], name=c[1], arguments=c[2]) for c in calls])
def U(text): return N(role="user", content=text)
def T(i, content, err=False): return N(role="tool", id=i, content=content, error=err)
auth = [A(calls=[("a1", "find_user_id_by_email", {"email": "x@y.com"})]), T("a1", "user_123")]
order = lambda st: [A(calls=[("o1", "get_order_details", {"order_id": "#W1"})]), T("o1", json.dumps({"order_id": "#W1", "status": st}))]
cancel = A(calls=[("c1", "cancel_pending_order", {"order_id": "#W1", "reason": "no longer needed"})])
ok_hist = auth + order("pending") + [A("I will cancel order #W1. Confirm?"), U("Yes, please go ahead.")]
assert guard.check(cancel, ok_hist) is None
assert guard.check(cancel, order("pending") + [U("yes")])[0] == "auth"
assert guard.check(cancel, auth + order("pending") + [U("Hmm, what are my options?")])[0] == "confirm"
assert guard.check(cancel, auth + order("pending") + [U("No, wait.")])[0] == "confirm"
assert guard.check(cancel, auth + [U("yes")])[0] == "status_unknown"
assert guard.check(cancel, auth + order("delivered") + [U("yes")])[0] == "status"
ret = A(calls=[("r1", "return_delivered_order_items", {"order_id": "#W1", "item_ids": ["1"]})])
assert guard.check(ret, auth + order("delivered") + [U("yes")]) is None
mod = A(calls=[("m2", "modify_pending_order_items", {"order_id": "#W1"})])
prev = [A(calls=[("m1", "modify_pending_order_items", {"order_id": "#W1"})]), T("m1", json.dumps({"status": "pending (items modified)"}))]
assert guard.check(mod, auth + order("pending") + prev + [U("yes")])[0] == "once"
assert guard.check(A(calls=[("x", "get_order_details", {}), ("y", "get_user_details", {})]), [])[0] == "one_call"
assert guard.check(A(calls=[("g", "get_order_details", {"order_id": "#W1"})]), []) is None      # reads pass through
assert guard.check(cancel, [A(calls=[("a1", "find_user_id_by_email", {})]), T("a1", "Error: user not found", err=True), U("yes")] + order("pending"))[0] in ("auth", "confirm")
assert all(r in guard.FALLBACK for r in ("auth", "confirm", "status", "status_unknown", "once", "one_call"))
print("all tests passed")
