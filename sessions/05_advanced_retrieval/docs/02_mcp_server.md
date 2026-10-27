# Optional · The knowledge base as an MCP server

**What you do**: serve the hybrid search of notebook 02 as the MCP tool `search_kb` (`app/kb_mcp_server.py`,
[FastMCP](https://gofastmcp.com/)), then use it from Claude Desktop, Cursor, Claude Code or another agent.

| Tool | Arguments | Returns |
|---|---|---|
| `search_kb(query, effective_after=None)` | Vietnamese query; optional date `YYYY-MM-DD` | the 8 best passages, each with `[title \| trang N \| hiệu lực YYYY-MM-DD]` |

The access groups are **fixed when the server starts** (`--groups`, default `public`): the model cannot widen them.
Run one server per audience; a public server (`--public`) also requires an API key.

## 0. Before you start
- Qdrant running and the collection built: `docker compose up -d`, then notebook 02 (or `uv run app/ingest.py`).
- `.env` with `OPENAI_API_KEY` (the server embeds the queries); for a public URL also `NGROK_AUTHTOKEN` and
  `KB_READ_KEY` ([README, setup step 3](../README.md#3-set-up-env)).
- A terminal in the session folder with `UV_PROJECT_ENVIRONMENT=venvAE05` (README, setup step 1).

## 1. Three ways to run it

| Command | Who can connect | Key |
|---|---|---|
| `uv run app/kb_mcp_server.py` (stdio) | the app that starts it (Claude Desktop, Cursor, Claude Code) | none |
| `uv run app/kb_mcp_server.py --http` | apps on this machine: `http://localhost:8005/mcp` | none |
| `uv run app/kb_mcp_server.py --http --public` | anyone with the https URL (claude.ai, apps on other machines) | `KB_READ_KEY` |

```bash
uv run app/kb_mcp_server.py --http                          # http://localhost:8005/mcp, groups: public
uv run app/kb_mcp_server.py --http --groups public,finance  # a finance-team server, on this machine only
uv run app/kb_mcp_server.py --http --public                 # plus a public https URL from ngrok
```

The server listens on `127.0.0.1` only; `--public` opens an [ngrok](https://ngrok.com/docs/getting-started/python/)
tunnel with the `ngrok` Python package (no ngrok command to install) that forwards a public https URL to it. Ctrl+C
stops the server and the tunnel. It logs the URL and one line per search:

```text
$ uv run app/kb_mcp_server.py --http --public
INFO | MCP server gia-dien-kb: http://localhost:8005/mcp (groups: public, API key required)
INFO | Public URL: https://<name>.ngrok-free.dev/mcp
INFO | search_kb('giá điện sinh hoạt bậc 1', after=None, groups=public) -> ok 846 ms
```

**A public URL needs a key.** Anyone who finds the URL could search, and every search costs an OpenAI embedding call.
With `--public` the server checks `Authorization: Bearer <KB_READ_KEY>` on every request (FastMCP
`StaticTokenVerifier`, as `shop_server_auth.py` in Session 03); no key or a wrong key gets HTTP 401. The key applies to
localhost too (same server). Keep the default `--groups public` on a public server: never publish the finance documents.

## 2. Connect an app

Replace `<paste KB_READ_KEY from .env>` with the value of `KB_READ_KEY` from `.env`. Without `--public`, use
`http://localhost:8005/mcp` and drop the header.

**Cursor** (`.cursor/mcp.json` in your project, or `~/.cursor/mcp.json`), then **Cursor Settings → MCP** shows
`gia-dien-kb` with 1 tool:

```json
{ "mcpServers": { "gia-dien-kb": { "url": "https://<name>.ngrok-free.dev/mcp",
                                   "headers": { "Authorization": "Bearer <paste KB_READ_KEY from .env>" } } } }
```

**Claude Code**:

```bash
claude mcp add --transport http gia-dien-kb https://<name>.ngrok-free.dev/mcp --header "Authorization: Bearer <paste KB_READ_KEY from .env>"
claude mcp list                                   # gia-dien-kb: ... - ✔ Connected
```

**Claude (claude.ai or Claude Desktop)** connects from Anthropic's cloud, so it needs the https URL:
**Customize → Connectors → Add custom connector** → name `gia-dien-kb`, the URL, authentication **No sign-in**, then
**Request headers** `Authorization: Bearer <key>`. Request headers are in beta for some organizations only; without
them, use Claude Desktop with stdio (below) or Claude Code.

**Claude Desktop (stdio, the app starts the server, no key)**: *Settings → Developer → Edit Config*, with the absolute
path of this folder, then restart the app:

```json
{ "mcpServers": { "gia-dien-kb": { "command": "uv",
                                   "args": ["run", "--directory", "/abs/path/sessions/05_advanced_retrieval", "app/kb_mcp_server.py"],
                                   "env": { "UV_PROJECT_ENVIRONMENT": "venvAE05" } } } }
```

`env` makes `uv` use `venvAE05`. If the app says `uv` is not found, put the full path of `uv` in `command`
(`which uv`; Windows `where.exe uv`).

**Another agent (Python)**: FastMCP's client sends the key as the bearer token:

```python
from fastmcp import Client

async with Client("https://<name>.ngrok-free.dev/mcp", auth="<paste KB_READ_KEY from .env>") as client:
    print([t.name for t in await client.list_tools()])            # ['search_kb']
    print((await client.call_tool("search_kb", {"query": "giá điện sinh hoạt bậc 1"})).content[0].text[:300])
```

Then ask: *"Dùng gia-dien-kb: giá điện sinh hoạt bậc 1 hiện nay là bao nhiêu?"*

**Keep the key out of shared config files**: reference an environment variable instead, `$KB_READ_KEY` in the
`claude mcp add` command, `${KB_READ_KEY}` in Claude Code's `.mcp.json`, `${env:KB_READ_KEY}` in Cursor's `mcp.json`.
The variable must exist where the app runs (`.env` is read only by this lab's code): `export KB_READ_KEY=<key>`
(PowerShell `$env:KB_READ_KEY="<key>"`), then start `claude` or `cursor` from that terminal.

## Troubleshooting
- `--public needs NGROK_AUTHTOKEN` / `KB_READ_KEY`: fill it in `.env` (README, setup step 3).
- `ngrok did not start: … endpoint 'https://<name>.ngrok-free.dev' is already online` (ERR_NGROK_334): the free plan
  gives your account one fixed domain, and another `--public` server with the same authtoken is still running (Session
  03's, another terminal, another machine). Stop it, then start again. Other `ngrok did not start` errors: wrong
  `NGROK_AUTHTOKEN` or no network.
- `401 Unauthorized`: the app sends no key or an old one; check the `Authorization: Bearer …` header.
- The app cannot reach the server: use the https URL with `/mcp` and keep the terminal running.

## Why not `mcp-server-qdrant`?
The official [`mcp-server-qdrant`](https://github.com/qdrant/mcp-server-qdrant) works on collections it creates
itself: one dense vector named after its FastEmbed model and a payload `{document, metadata}`. It does not know the
`dense` / `bm25` vectors, the hybrid query or the access filter of `gia_dien`. Use it on a separate collection (for
example as an agent memory with `qdrant-store` / `qdrant-find`), not on this one.

## References
- FastMCP: https://gofastmcp.com/
- FastMCP bearer tokens: https://gofastmcp.com/servers/auth/token-verification · client: https://gofastmcp.com/clients/auth/bearer
- MCP, connect to local servers: https://modelcontextprotocol.io/docs/develop/connect-local-servers · remote servers: https://modelcontextprotocol.io/docs/develop/connect-remote-servers
- ngrok Python SDK: https://ngrok.com/docs/getting-started/python/
- Claude custom connectors: https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp
- Cursor MCP: https://cursor.com/docs/mcp · Claude Code MCP: https://code.claude.com/docs/en/mcp
