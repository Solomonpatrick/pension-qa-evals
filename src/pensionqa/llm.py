"""One small interface over the model provider, plus a fake for tests."""
from dataclasses import dataclass, field

from pensionqa import config


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    input_tokens: int = 0
    output_tokens: int = 0
    content: list = field(default_factory=list)   # raw blocks, appended to history unchanged


class AnthropicLLM:
    def __init__(self, model: str, effort: str | None = None, client=None):
        import anthropic
        self.model, self.effort = model, effort
        self.client = client or anthropic.Anthropic()   # reads ANTHROPIC_API_KEY

    def complete(self, system, messages, tools=None, json_schema=None, max_tokens=4000) -> LLMResponse:
        kwargs = {"model": self.model, "max_tokens": max_tokens, "system": system, "messages": messages}
        output_config = {}
        if self.effort:
            output_config["effort"] = self.effort
        if json_schema:
            output_config["format"] = {"type": "json_schema", "schema": json_schema}
        if output_config:
            kwargs["output_config"] = output_config
        if tools:
            kwargs["tools"] = tools
        resp = self.client.messages.create(**kwargs)
        return LLMResponse(
            text="".join(b.text for b in resp.content if b.type == "text"),
            tool_calls=[ToolCall(b.id, b.name, b.input) for b in resp.content if b.type == "tool_use"],
            stop_reason=resp.stop_reason,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            content=resp.content,
        )


class FakeLLM:
    """Replays scripted responses in order, then a default. Items can be an LLMResponse, a string,
    or a function(system, messages) that returns either."""

    def __init__(self, script=None, default="I can't find that in the guidance provided."):
        self.script, self.default, self.calls = list(script or []), default, []

    def complete(self, system, messages, tools=None, json_schema=None, max_tokens=4000) -> LLMResponse:
        self.calls.append({"system": system, "messages": list(messages), "tools": tools, "json_schema": json_schema})
        item = self.script.pop(0) if self.script else self.default
        if callable(item):
            item = item(system, messages)
        return fake_text(item) if isinstance(item, str) else item


def fake_text(text: str) -> LLMResponse:
    return LLMResponse(text=text, content=[{"type": "text", "text": text}])


def fake_tool_call(name: str, args: dict, call_id: str = "toolu_1") -> LLMResponse:
    return LLMResponse(text="", tool_calls=[ToolCall(call_id, name, args)], stop_reason="tool_use",
                       content=[{"type": "tool_use", "id": call_id, "name": name, "input": args}])


def get_llm(role: str = "answer"):
    if config.LLM_MODE == "fake":
        return FakeLLM()
    if role == "judge":
        return AnthropicLLM(config.JUDGE_MODEL, config.JUDGE_EFFORT)
    return AnthropicLLM(config.ANSWER_MODEL, config.ANSWER_EFFORT)
