import json
import os
import threading
import time

from dotenv import load_dotenv

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_REPO_ROOT, ".env"))

from .backends import BACKENDS, ContentFiltered, MissingSDK
from .limiter import window_for
from .registry import MODELS, ROLES, available, names, pin, resolve, roles

MAX_ATTEMPTS = int(os.environ.get("LLM_MAX_ATTEMPTS", "3"))
BACKOFF = 1.5

_clients = {}
_lock = threading.Lock()


def _client(spec):
    key = (spec["kind"], spec["base_url"], spec["auth_header"])
    with _lock:
        if key not in _clients:
            _clients[key] = BACKENDS[spec["kind"]](spec)
        return _clients[key]


def _estimate(text):
    return max(1, len(text) // 4)


def _retry_after(exc):
    resp = getattr(exc, "response", None)
    if resp is None:
        return None
    try:
        return float(resp.headers.get("retry-after"))
    except (TypeError, ValueError):
        return None


def _strip_fence(raw):
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw[:4].lower() == "json":
            raw = raw[4:]
    return raw.strip()


def complete(system, user, max_tokens, role=None, model=None,
             attempts=MAX_ATTEMPTS, as_json=False):
    spec = resolve(role=role, model=model)
    backend = _client(spec)
    budget = window_for(spec["name"], spec["tpm"])
    max_tokens = min(max_tokens, spec["max_out"])
    prompt_cost = _estimate(system) + _estimate(user)
    last = None
    for i in range(attempts):
        item = budget.reserve(prompt_cost + max_tokens)
        try:
            raw, used = backend.complete(spec, system, user, max_tokens)
        except MissingSDK:
            budget.settle(item, 0)
            raise
        except Exception as e:
            budget.settle(item, prompt_cost)
            last = e
        else:
            budget.settle(item, used)
            if not as_json:
                return raw
            try:
                return json.loads(_strip_fence(raw))
            except ValueError as e:
                last = e
        if i + 1 < attempts:
            time.sleep(_retry_after(last) or BACKOFF * (2 ** i))
    raise RuntimeError(f"{spec['name']} failed after {attempts} attempt(s): {last}") from last


def complete_json(system, user, max_tokens, role=None, model=None, attempts=MAX_ATTEMPTS):
    return complete(system, user, max_tokens, role=role, model=model,
                    attempts=attempts, as_json=True)


def describe():
    out = {"available": available(), "roles": {}}
    if not available():
        return out
    for role in roles():
        spec = resolve(role=role)
        out["roles"][role] = {"alias": spec["name"], "id": spec["id"],
                              "kind": spec["kind"], "tpm": spec["tpm"]}
    return out
