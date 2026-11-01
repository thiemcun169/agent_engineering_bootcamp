url: https://docs.example.test/langchain/middleware-notes
title: LangChain agent middleware (fake class notes)

# LangChain agent middleware

> Fake teaching notes for the Session 08 lab. They paraphrase the LangChain middleware docs and are not the official page.

Middleware wraps the agent loop. You pass a list to `create_agent(..., middleware=[...])` and each item can hook into a different point.

## Hooks
- `before_agent` runs once when the run starts: good for a scope check or loading memory. It can end the run early with `jump_to: "end"`.
- `before_model` / `after_model` run around every model call: redact input, validate output, ask for approval.
- `wrap_model_call` and `wrap_tool_call` wrap the call itself, so they can retry, replace or block it. `wrap_tool_call(request, handler)` is where an audit log or a permission check belongs.

## Built-in middleware
- `PIIMiddleware` detects emails, credit cards, IPs, URLs and custom patterns, then `redact`, `mask`, `hash` or `block`. With `apply_to_tool_results=True` it also cleans tool results before the model reads them.
- `HumanInTheLoopMiddleware(interrupt_on={"tool": {...}})` stops before a sensitive tool and waits for approve, edit or reject. It needs a checkpointer.

## Order matters
Middleware runs in list order for `before_*` hooks and in reverse order for `after_*` hooks, so put cheap deterministic guards first.
