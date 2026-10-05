# Session 03 — Tool and MCP Engineering

Give an agent real tools, then share them with any AI application. You write SQL tools over a small online store
database, serve them from your own **MCP server** that Claude, Cursor or any agent can use by URL, then protect the
server with **API keys** and connect the agent to **Notion with an OAuth sign-in**. From this session on the labs use
LangChain `create_agent`.

## Parts

| Part                               | Start the server (terminal)                             | Then open                                                       | Steps and apps                                                                   |
| ---------------------------------- | ------------------------------------------------------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 1 · SQL tools for an agent        | none (tools run in the notebook)                        | [01_sql_tools_agent.ipynb](notebooks/01_sql_tools_agent.ipynb)   | [docs/01_sql_tools.md](docs/01_sql_tools.md)                                      |
| 2 · Remote MCP server, no sign-in | `uv run app/shop_server.py --http [--public]`         | [02_remote_mcp_agent.ipynb](notebooks/02_remote_mcp_agent.ipynb) | [docs/02_remote_mcp.md](docs/02_remote_mcp.md): Claude, Cursor, Claude Code       |
| 3 · API keys and OAuth sign-in    | `uv run app/shop_server_auth.py [--public] [--reset]` | [03_auth_mcp_agent.ipynb](notebooks/03_auth_mcp_agent.ipynb)     | [docs/03_auth.md](docs/03_auth.md): keys in other apps, Notion, other MCP servers |

Explanations are in the notebooks. Each notebook ends with a demo cell (`question = "..."`, edit it and run again)
whose answer **streams** token by token, with one line per tool call and result.

## Setup

You need [uv](https://docs.astral.sh/uv/) and VS Code or Cursor with the **Python** and **Jupyter** extensions
(install steps in the [repository README](../../README.md)). Open a terminal **in this folder**:

```bash
cd sessions/03_tool_mcp
```

On Windows, use **PowerShell** for the commands below.

### 1. Create the environment `venvAE03`

uv downloads Python 3.12 if needed and installs the exact versions of `uv.lock`:

```bash
export UV_PROJECT_ENVIRONMENT=venvAE03 && uv sync              # macOS / Linux
```

```powershell
$env:UV_PROJECT_ENVIRONMENT="venvAE03"; uv sync                # Windows PowerShell
```

`UV_PROJECT_ENVIRONMENT` tells every later `uv run` in this terminal to use `venvAE03`; set it again in each new terminal.

### 2. Register it as a notebook kernel

Named `venvAE03`:

```bash
uv run python -m ipykernel install --user --name venvAE03 --display-name venvAE03
```

Same command on every OS, in the terminal where you set `UV_PROJECT_ENVIRONMENT` (step 1).

### 3. Set up `.env`

Copy `.env.example` to `.env` in this folder (`cp .env.example .env`; Windows `Copy-Item .env.example .env`), open
`.env` and paste the keys (no quotes, no spaces around `=`). The notebooks and the servers read this file; restart
the kernel after you change it. Part 1 needs `OPENAI_API_KEY` (and `MODEL`, any `provider:model` of LangChain
`init_chat_model`); part 2 adds `TAVILY_API_KEY`; part 3 adds the shop keys and the token store key.

- **OpenAI** (`OPENAI_API_KEY`)
  1. Sign in at https://platform.openai.com.
  2. **Settings → Billing**: add a payment method and a few dollars of credit (the API does not run on a ChatGPT subscription).
  3. **API keys** (https://platform.openai.com/api-keys) → **Create new secret key** → copy the key (`sk-…`); it is shown only once.
- **Tavily** (`TAVILY_API_KEY`)
  1. Sign up at https://app.tavily.com (Google or email); the free plan is enough for the labs.
  2. On the dashboard, copy the default key (`tvly-…`) or create one under **API Keys**.
- **Shop API keys** (`SHOP_READ_KEY`, `SHOP_WRITE_KEY`, part 3): two different long random strings; make each one with
  `uv run python -c "import secrets; print(secrets.token_urlsafe(24))"` (run it twice).
- **Ports** (`SHOP_PORT=8000`, part 2; `SHOP_AUTH_PORT=8001`, part 3): change one if it is busy. The notebooks connect
  to `http://localhost:<port>/mcp`; to test the public URL instead, set the optional `SHOP_MCP_URL` /
  `SHOP_AUTH_MCP_URL` to the `https://…/mcp` URL logged by `--public`.
- **Notion** (part 3): a free account at https://www.notion.so. No key: you sign in from the notebook the first time.
- **Token store key** (`OAUTH_STORAGE_ENCRYPTION_KEY`, part 3): encrypts the stored Notion sign-in; make it with
  `uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
- **ngrok** (`NGROK_AUTHTOKEN`, optional: a public URL for the MCP server, needed by claude.ai / Claude Desktop)
  1. Sign up at https://dashboard.ngrok.com/signup → **Your Authtoken** → copy it into `NGROK_AUTHTOKEN` in `.env`.
  2. Nothing to install: `--public` opens the tunnel with the `ngrok` Python package (already in `uv.lock`).

### 4. Open the lab in VS Code or Cursor

1. **File → Open Folder… → `sessions/03_tool_mcp`** (this folder, not the whole repository).
   Accept the prompt to install the recommended extensions if they are missing.
2. Open a notebook in `notebooks/` → **Select Kernel** (top right) → **Jupyter Kernel…** → **venvAE03**
   (or **Python Environments… → venvAE03**). If `venvAE03` is not listed, run **Developer: Reload Window** from the
   Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) and try again.
3. Run the cells one by one (`Shift+Enter`). `INFO | …` lines are logs (diagnostics from the code and servers);
   `→` / `←` lines and the answer are the agent's streamed output.

### 5. Run a part

Start its server in a terminal opened in this folder (parts 2 and 3), keep it running, then open the
notebook (same commands on every OS, after setting `UV_PROJECT_ENVIRONMENT` as in step 1):

```bash
uv run app/shop_server.py --http               # part 2, add --public for an https URL (Claude)
uv run app/shop_server_auth.py                 # part 3, --public as above, --reset for a fresh database copy
uv run pytest -q                               # tests
```

## Troubleshooting

- `venvAE03` not in the kernel list: run step 2, install the **Jupyter** extension, open this folder (not the repository root), then **Developer: Reload Window**.
- `No MCP server at ...` in notebook 02 or 03: start the server of that part (step 5); the ports are in `.env`
  (`SHOP_PORT`, `SHOP_AUTH_PORT`; remove `SHOP_MCP_URL` / `SHOP_AUTH_MCP_URL` if an old ngrok URL is still there).
- `Missing ...` in the first cell: fill that key in `.env` (step 3).
- `uv run` creates a `.venv` folder: `UV_PROJECT_ENVIRONMENT` is not set in this terminal; set it (step 1), delete `.venv`.
- Notion sign-in on a remote machine, ngrok, Claude or Cursor problems: see the troubleshooting part of each doc.

## References

- Tools: https://docs.langchain.com/oss/python/langchain/tools · https://www.anthropic.com/engineering/writing-tools-for-agents
- SQL agent: https://docs.langchain.com/oss/python/langchain/sql-agent
- MCP: https://modelcontextprotocol.io/docs/learn/architecture · https://gofastmcp.com · https://docs.langchain.com/oss/python/langchain/mcp
- Authorization: https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization
