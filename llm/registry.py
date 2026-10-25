import os

MODELS = {
    "sonnet-4.5": {"kind": "anthropic", "path": "/anthropic", "id": "claude-sonnet-4-5",
                   "auth_header": "x-api-key", "token_param": "max_tokens", "max_out": 8192},
    "sonnet-4.6": {"kind": "anthropic", "path": "/anthropic", "id": "claude-sonnet-4-6",
                   "auth_header": "x-api-key", "token_param": "max_tokens", "max_out": 8192},
    "gpt-5.4": {"kind": "openai", "path": "/openai/v1", "id": "gpt-5.4",
                "auth_header": "api-key", "token_param": "max_completion_tokens",
                "max_out": 16384},
    "gpt-4.1": {"kind": "openai", "path": "/openai/v1", "id": "gpt-4.1",
                "auth_header": "api-key", "token_param": "max_tokens", "max_out": 8192},
    "gpt-4o": {"kind": "openai", "path": "/openai/v1", "id": "gpt-4o",
               "auth_header": "api-key", "token_param": "max_tokens", "max_out": 4096},
    "llama-4-maverick": {"kind": "openai", "path": "/openai/v1",
                         "id": "Llama-4-Maverick-17B-128E-Instruct-FP8",
                         "auth_header": "api-key", "token_param": "max_tokens",
                         "max_out": 4096},
}

ROLES = {
    "writer": "sonnet-4.5",
    "bible": "sonnet-4.5",
    "handle": "gpt-4o",
    "profiler": "sonnet-4.6",
}

BASE_URL_VAR = "PATAI_BASE_URL"
KEY_VAR = "PATAI_API_KEY"
TPM_DEFAULT = 50000

_pins = {}


def names():
    return sorted(MODELS)


def roles():
    return sorted(ROLES)


def pin(role, model_name):
    if model_name not in MODELS:
        raise ValueError(f"unknown model '{model_name}'; have {names()}")
    _pins[role] = model_name


def _slug(name):
    return name.upper().replace("-", "_").replace(".", "_")


def resolve(role=None, model=None):
    name = model
    if name is None:
        if role is None:
            raise ValueError("resolve needs a role or a model")
        name = (_pins.get(role)
                or os.environ.get("LLM_ROLE_" + _slug(role))
                or ROLES.get(role))
        if name is None:
            raise ValueError(f"no model mapped for role '{role}'; have {roles()}")
    if name not in MODELS:
        raise ValueError(f"unknown model '{name}'; have {names()}")
    spec = dict(MODELS[name])
    spec["name"] = name
    spec["id"] = os.environ.get("LLM_ID_" + _slug(name), spec["id"])
    spec["path"] = os.environ.get("LLM_PATH_" + _slug(name), spec["path"])
    spec["auth_header"] = os.environ.get("LLM_AUTH_" + _slug(name), spec["auth_header"])
    spec["key"] = os.environ.get(KEY_VAR)
    spec["base_url"] = (os.environ.get(BASE_URL_VAR) or "").rstrip("/") + spec["path"]
    spec["tpm"] = int(os.environ.get("LLM_TPM_" + _slug(name),
                                     os.environ.get("LLM_TPM_DEFAULT", TPM_DEFAULT)))
    return spec


def available():
    if os.environ.get("LLM_OFFLINE") == "1":
        return False
    return bool(os.environ.get(KEY_VAR) and os.environ.get(BASE_URL_VAR))
