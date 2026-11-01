# Session 08 — Security, Guardrails and Governance

Attack the **Research Brief Agent** of the course, then defend it. In Notebook 1 you talk to the baseline agent like a normal chat and make it do
things it must never do: email data to an attacker because a web page told it to (indirect prompt injection), read Bob's private note and the
finance budget (cross-user leak), print its system prompt key and customer phone numbers (data leakage), act on a poisoned memory note.
In Notebook 2 you build **one defended agent** with `create_agent` and a middleware stack (scope guard, PII redaction, human approval), permissions
checked **in the tool** instead of the prompt, an egress allowlist, an audit log and tool pinning — then run baseline vs defended on the 14 cases
and compare the attack-success and utility rates. The lab is self-contained: all pages, knowledge base entries and users are fake, and nothing
leaves your machine (`send_report` writes to `output/outbox.jsonl`).

**Two models on purpose.** Notebook 1 pins a smaller model (`gpt-4.1-mini`): a capable model such as the session `gpt-6-luna` refuses most of these
requests, which *hides* the holes. Newer models are trained to resist prompt injection, so how often an attack succeeds depends on the model — a
refusal does **not** mean the agent is safe. The holes are in the agent's **design** (the tool obeys its arguments, the prompt trusts data, there
is no team filter or egress check), not the model: Notebook 2 defends the session model and still blocks the attacks even on the small model that
followed them. Each notebook defines a short `chat()` helper and builds the agent inline; every attack and the 14 cases are **written out in the
code** (`app/cases.py`), nothing loaded from an opaque file. There are no `assert`s — each attack prints what happened and the design flaw behind
it, numbered like the slide's defence map (controls 1–7); a tool-layer replay proves the hole with no model at all.

## Notebooks
| Notebook | What you do |
|---|---|
| [01_attack_the_agent.ipynb](notebooks/01_attack_the_agent.ipynb) | Attack the Research Brief Agent |
| [02_defend_and_test.ipynb](notebooks/02_defend_and_test.ipynb) | Defend the agent and keep the defences with tests |

The notebooks contain the full solution; explanations are inline, and each cell prints the agent's **real steps** (every tool call and result)
so you can see where a guard fires. `app/` holds the agent (`agent_lib.py`: tools, prompts, `build_model`) and the controls (`guards.py`); the 14
cases live in `app/cases.py` (loaded by the notebooks and the tests); `data/` holds the fake pages, knowledge base and users.

**One control uses a model.** The indirect-injection guard (`injection_guard`) can't be a regex — you don't know an injected
instruction's wording in advance — so it asks the **OpenAI Decisions API** (`client.decisions.create`, model `gpt-6-luna`) one yes/no
question about each **data** tool result (read_doc, search_docs, search_kb, get_profile — not the action tools, whose status line can itself
read as an instruction) and withholds the result above a probability threshold (and fails closed, withholding, if the model refuses to judge). In the lab a hostile page scores ~1.0 and a clean page ~0.0 (~0.4s per call). Every other control is plain code. The offline tests
(`pytest -m security`, 14 of them) need no key: they call the tools and guard functions directly, passing a fake checker to the injection guard.

## Setup
You need [uv](https://docs.astral.sh/uv/) and VS Code or Cursor with the **Python** and **Jupyter** extensions
(install steps in the [repository README](../../README.md)). Open a terminal **in this folder**:
```bash
cd sessions/08_security_guardrails
```
On Windows, use **PowerShell** for the commands below.

**1. Create the environment `venvAE08`** (uv downloads Python 3.12 if needed and installs the exact versions of `uv.lock`):
```bash
UV_PROJECT_ENVIRONMENT=venvAE08 uv sync                      # macOS / Linux
```
```powershell
$env:UV_PROJECT_ENVIRONMENT="venvAE08"; uv sync              # Windows PowerShell
```

**2. Register it as a notebook kernel** named `venvAE08`:
```bash
venvAE08/bin/python -m ipykernel install --user --name venvAE08 --display-name venvAE08        # macOS / Linux
```
```powershell
venvAE08\Scripts\python -m ipykernel install --user --name venvAE08 --display-name venvAE08    # Windows
```

**3. Add your OpenAI key**: copy `.env.example` to `.env` in this folder (`cp .env.example .env`; Windows
`Copy-Item .env.example .env`), open `.env` and paste the key.
- **OpenAI** (`OPENAI_API_KEY`)
  1. Sign in at https://platform.openai.com.
  2. **Settings → Billing**: add a payment method and a few dollars of credit (the API does not run on a ChatGPT subscription).
  3. **API keys** (https://platform.openai.com/api-keys) → **Create new secret key** → copy the key (`sk-…`); it is shown only once.

`MODEL` is already set to the session model; the attack notebook pins `gpt-4.1-mini` on its own.

**4. Open the lab in VS Code or Cursor**
1. **File → Open Folder… → `sessions/08_security_guardrails`** (this folder, not the whole repository).
   Accept the prompt to install the recommended extensions if they are missing.
2. Open a notebook in `notebooks/` → **Select Kernel** (top right) → **Jupyter Kernel…** → **venvAE08**
   (or **Python Environments… → venvAE08**). If `venvAE08` is not listed, run **Developer: Reload Window** from the
   Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) and try again.
3. Run the cells one by one (`Shift+Enter`). Log lines (`INFO | …`) show each step while the code runs.

All data is fake (`data/`). Offline security tests (no key needed): `venvAE08/bin/python -m pytest -m security`.

## Troubleshooting
- `venvAE08` not in the kernel list: run step 2, install the **Jupyter** extension, open this folder (not the repository root), then **Developer: Reload Window**.
- `RuntimeError: tool pinning failed`: you changed a tool name, description or argument schema. If that was deliberate, run `python -m app.agent_lib --write-lock` in this folder and commit `data/tools.lock.json`.
- An attack "did not send this time" / "refused all tries": the model resisted this run (a model follows an injected instruction only some of the time). Run the cell again. The tool-layer replay cell never depends on the model, so it proves the hole regardless.
- The memory-poisoning attack is the least reliable on `gpt-4.1-mini`; the cell first proves the memory is poisoned (the note comes back from `get_profile`) and then reports the model's hit rate honestly.
- `GraphRecursionError` in your own experiments: the model kept retrying a blocked call. The `BLOCKED` tool message says "do not retry"; `chat()` returns what happened so far.
- `HumanInTheLoopMiddleware` needs a checkpointer and a `thread_id`; the defended agent passes `InMemorySaver`, and `chat()` sets the thread id. Resume with `Command(resume={"decisions": [...]})` (shown once in Notebook 2).
- Never commit `.env` or the contents of `output/`.

## References
- LangChain: [Guardrails](https://docs.langchain.com/oss/python/langchain/guardrails) · [Built-in middleware (PIIMiddleware, HumanInTheLoopMiddleware)](https://docs.langchain.com/oss/python/langchain/middleware/built-in) · [Custom middleware (before_agent, wrap_tool_call)](https://docs.langchain.com/oss/python/langchain/middleware/custom) · [Human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) · [Runtime context](https://docs.langchain.com/oss/python/langchain/runtime)
- OWASP: [LLM01 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) · [LLM02 Sensitive Information Disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/) · [LLM06 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/)
- Simon Willison, [The lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/)
