class MissingSDK(RuntimeError):
    pass


class ContentFiltered(RuntimeError):
    pass


class AnthropicBackend:
    def __init__(self, spec):
        try:
            import anthropic
        except ImportError as e:
            raise MissingSDK(
                f"model '{spec['name']}' needs the anthropic SDK: pip install anthropic") from e
        kwargs = {"api_key": spec["key"], "base_url": spec["base_url"], "max_retries": 0}
        if spec["auth_header"].lower() != "x-api-key":
            kwargs["default_headers"] = {spec["auth_header"]: spec["key"]}
        self.client = anthropic.Anthropic(**kwargs)

    def complete(self, spec, system, user, max_tokens):
        msg = self.client.messages.create(
            model=spec["id"], system=system,
            messages=[{"role": "user", "content": user}],
            **{spec["token_param"]: max_tokens},
        )
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        used = msg.usage.input_tokens + msg.usage.output_tokens
        if not text:
            raise RuntimeError(f"{spec['name']} returned no text (stop={msg.stop_reason})")
        return text, used


class OpenAIBackend:
    def __init__(self, spec):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise MissingSDK(
                f"model '{spec['name']}' needs the openai SDK: pip install openai") from e
        headers = None
        if spec["auth_header"].lower() != "authorization":
            headers = {spec["auth_header"]: spec["key"]}
        self.client = OpenAI(api_key=spec["key"], base_url=spec["base_url"],
                             default_headers=headers, max_retries=0)

    def complete(self, spec, system, user, max_tokens):
        r = self.client.chat.completions.create(
            model=spec["id"],
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            **{spec["token_param"]: max_tokens},
        )
        choice = r.choices[0]
        used = r.usage.total_tokens if r.usage else 0
        if choice.finish_reason == "content_filter":
            raise ContentFiltered(f"{spec['name']} blocked by Azure content filter")
        text = (choice.message.content or "").strip()
        if not text:
            raise RuntimeError(
                f"{spec['name']} returned empty content (finish={choice.finish_reason})")
        return text, used


BACKENDS = {"anthropic": AnthropicBackend, "openai": OpenAIBackend}
