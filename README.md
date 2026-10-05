# Agent Engineering — Labs

**Build Modern, Secure and Reliable AI Agents** · COLE

Hands-on labs of the Agent Engineering course: build a modern AI agent that plans, uses tools, retrieves knowledge,
keeps context, coordinates with other agents and checks its own results. 10 sessions × 2 hours.

## Syllabus

| #  | Session                                             | Topics                                                                                                                                                                                                                                         |
| -- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 01 | Modern Agent Systems and Harness                    | LLM foundations for agents (reasoning, tool calling); from workflows to agents; Agent = Model + Harness; how Claude Code, ChatGPT and Cursor organise context, tools, memory and execution                                                     |
| 02 | Agent Loop Engineering with LangGraph               | LangGraph building blocks; the Thought → Action → Observation loop coded with LangGraph; state, checkpoints, human approval, retry, resume, streaming; loop control                                                                          |
| 03 | Tool and MCP Engineering                            | function calling; designing reliable, testable tools; database, SQL, RAG, API and sandbox tools; MCP host, client, server; least privilege, authentication, authorization, audit                                                               |
| 04 | Context Engineering with Prompts, Skills and Memory | what makes up an agent's context; managing context for long tasks; prompts, Skills, short- and long-term memory; filesystem and artifacts; safe multi-user context                                                                             |
| 05 | Advanced Retrieval and Vector Databases for Agents  | RAG and retrieval tools in the agent loop; embeddings, vector databases, indexing, metadata, filtering; advanced retrieval; relevance, citations, freshness, not-enough-evidence handling; multi-user knowledge bases                          |
| 06 | Multi-Agent Engineering                             | one agent with Skills or several specialists; subagent-as-tool/supervisor, handoff, router; delegation to independent async subagents; passing task, context and evidence; parallel execution, timeouts, partial failures                      |
| 07 | Observability and Evaluation Engineering            | why agents are hard to evaluate; tracing model, retrieval and tool use; eval datasets from product needs and failures; end-to-end, trajectory, tool and retrieval evaluation; code evaluators, LLM-as-a-judge, human review                    |
| 08 | Security, Guardrails and Governance                 | guardrails and out-of-scope requests; prompt injection, jailbreaks, poisoned context, data leakage, PII; authentication, authorization, per-user data; secure tool/MCP access, credentials, sandbox, approval; audit trails and security tests |
| 09 | Agent API Engineering with FastAPI                  | FastAPI fundamentals; Server-Sent Events for progress and tool activity; schemas, sessions, authentication, data isolation; error handling and health checks                                                                                   |
| 10 | Build Your Production-Ready Agent                   | choosing the architecture and building blocks for a use case; reviewing quality, safety and limits; preparing the agent for deployment and operations                                                                                          |

## How the repository works

Each session folder `sessions/NN_<slug>/` is an **independent lab**: its own README (goal, notebooks, setup),
`pyproject.toml` + `uv.lock` (exact package versions), `.env.example` (the keys it needs) and its own virtual
environment (`venvAE02` for Session 02, `venvAE03` for Session 03, …). You can start at any session.

What all sessions share:

- **[uv](https://docs.astral.sh/uv/)** to install Python and the packages (install it once, below);
- **Python 3.12**, installed by uv for each lab;
- **VS Code or Cursor** with the **Python** and **Jupyter** extensions: you open the session folder, then pick the
  session's kernel (`venvAE02`, `venvAE03`, …) in each notebook;
- API keys in a `.env` file inside the session folder (git-ignored, never committed).

## Install once (any computer: Windows, macOS, Linux)

1. **uv** (installs Python for you, no separate Python install needed)
   - macOS / Linux (Terminal): `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

   Close and reopen the terminal, then check: `uv --version`.
2. **git**: check `git --version`; if missing, install it from https://git-scm.com/downloads (Windows: keep the default
   options; macOS: `xcode-select --install` also works). Then clone the repository:
   ```bash
   git clone <this-repo-url> agent_engineering_bootcamp
   cd agent_engineering_bootcamp
   ```
3. **VS Code** (https://code.visualstudio.com/) or **Cursor** (https://cursor.com/). In the **Extensions** panel install
   **Python** (`ms-python.python`) and **Jupyter** (`ms-toolsai.jupyter`). Without the Jupyter extension the IDE cannot
   run notebooks or list kernels.

Then open the README of a session (for example [sessions/02_agent_loop_langgraph](sessions/02_agent_loop_langgraph/))
and follow its **Setup**: create the session environment, register its kernel, add the keys, open the session folder
in the IDE.

## Rules for every lab

- Run the setup commands **inside the session folder**; each lab keeps its environment there.
- Open **the session folder** in the IDE (File → Open Folder), not the whole repository: the IDE then finds that
  session's environment and its settings (`.vscode/`).
- In the notebook, check the kernel: `import sys; print(sys.executable)` must point into that session's `venvAENN` folder.
- Never commit `.env` or keys; do not `pip install` into a lab environment (add packages to its `pyproject.toml`).

Contributors: see [docs/lab_conventions.md](docs/lab_conventions.md).
