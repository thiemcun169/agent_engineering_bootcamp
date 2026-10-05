# Part 3 · An agent with authenticated MCP servers

**What you do**: your `shop` server now asks for an **API key** (`app/shop_server_auth.py`), and your agent also
connects to **Notion's MCP server with an OAuth sign-in**, the way Claude's connectors do. The agent writes a Q3 sales
analysis from the database and the web, then creates a Notion page with it.

| Server           | Credential                                          | What it allows                                                         |
| ---------------- | --------------------------------------------------- | ---------------------------------------------------------------------- |
| `shop` (yours) | `Authorization: Bearer <SHOP_READ_KEY>`           | scope`shop:read`: `list_tables`, `describe_table`, `run_query` |
|                  | `Authorization: Bearer <SHOP_WRITE_KEY>`          | +`shop:write`: `update_order_status`                               |
|                  | no key / unknown key                                | HTTP 401                                                               |
| `notion`       | OAuth 2.1 sign-in (browser), token stored encrypted | the pages you share at sign-in                                         |

## 0. `.env`

Needs, besides parts 1 and 2, `SHOP_AUTH_PORT` (default `8001`), two **different** keys `SHOP_READ_KEY` (scope `shop:read`) and `SHOP_WRITE_KEY` (`shop:read` + `shop:write`), and `OAUTH_STORAGE_ENCRYPTION_KEY` (encrypts the stored Notion sign-in); how to make each one: [README, setup step 3](../README.md#3-set-up-env). Notion needs no key, only a free account: notebook 03 opens the sign-in page the first time.

## 1. Start the server

`SHOP_READ_KEY` and `SHOP_WRITE_KEY` must be in `.env` and different (section 0). In a terminal in the session folder:

```bash
uv run app/shop_server_auth.py            # http://localhost:8001/mcp  (port: SHOP_AUTH_PORT)
uv run app/shop_server_auth.py --public   # plus a public https URL from ngrok (logged as `Public URL: ...`)
uv run app/shop_server_auth.py --reset    # start from a fresh copy of the database
```

Writes go to `output/shop.db` (a copy of `data/shop.db`, made on the first start). The server has two loggers: `shop` prints diagnostics to the terminal,
`shop.audit` writes one JSON line per tool call or refused request to `output/audit.jsonl`:

```text
WARNING | denied: HTTP 401 on /mcp (no or unknown key)
WARNING | denied: analyst calls update_order_status
INFO | describe_table('orders') -> ok 0 ms
INFO | run_query("SELECT 'category' AS section, p.category AS label, SUM(oi.quantity * …) -> ok 1 ms
```

```json
{"ts": "2026-10-04T14:04:38+00:00", "client_id": "analyst", "tool": "run_query", "args": {"sql": "SELECT ..."}, "status": "ok", "ms": 8}
{"ts": "2026-10-04T14:04:21+00:00", "client_id": null, "status": "denied", "http": 401, "path": "/mcp"}
```

**Audit log vs log.** An audit log is a security record: who did what, when, with which outcome. It is kept apart from
diagnostic logs and for longer ([OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html);
the [MCP spec](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) security considerations ask hosts to "Log tool usage for audit purposes"; our server does it where the key is checked). In code it is just a second Python logger
(`shop.audit`) with its own `FileHandler` and a JSON formatter.

## 2. Notebook 03

Open `notebooks/03_auth_mcp_agent.ipynb` and run it:

1. no key → 401; read key → 3 tools, the write tool is hidden (`Unknown tool`); write key → 4 tools;
2. the agent connects to `shop` and Notion with the code of the LangChain docs (section 3). **Notion**: the first time,
   connecting opens the sign-in page in the browser (the link is also logged as `OAuth authorization URL: ...`) and
   **waits** (5 minutes). Choose the pages the agent may use and click **Allow**; the notebook continues. Later runs
   reuse the token stored in `~/.cole-agent/oauth-tokens/`;
3. the agent (local tools + `shop` with the read key + 3 Notion tools) streams its work on the demo question: a Q3
   analysis saved as a new Notion page in "COLE Agent Reports". Where to save is the agent's choice: paste a Notion page
   link into the question to pick the page; otherwise it searches for the page you name, or creates a private page.

**Browser on another machine** (SSH, remote VS Code / Cursor): after **Allow** the page `localhost:8790/callback?...`
cannot load. Copy that full URL and run `curl '<url>'` on the machine where the notebook runs (or forward the port:
`ssh -L 8790:localhost:8790 <host>`).

## 3. How the agent connects: libraries only

No host code of our own: the notebook follows [LangChain MCP authentication](https://docs.langchain.com/oss/python/langchain/mcp/auth)
(per-server authentication) and the [FastMCP OAuth client](https://gofastmcp.com/clients/auth/oauth):

```python
servers = ClientGroup({
    "shop":   Client(SHOP_URL, auth=os.environ["SHOP_READ_KEY"]),        # API key: Authorization: Bearer <key>
    "notion": Client("https://mcp.notion.com/mcp", auth=notion_auth),     # OAuth(...) with an encrypted token store
})
async with MCPAdapter(servers) as mcp:
    tools = await mcp.list_tools()                                        # shop_run_query, notion_notion-search, ...
```

- One `Client` per server, each with its own credential; the `ClientGroup` keeps one connection per server and prefixes
  every tool with its key.
- `auth="<key>"` sends a bearer token. `auth="oauth"` runs the OAuth flow with default settings (tokens in memory: a new
  sign-in each run); `auth=OAuth(..., token_storage=...)` keeps the tokens on disk, encrypted with `FernetEncryptionWrapper`.
- Notion's `OAuth` registers as a public client (`token_endpoint_auth_method: none`, PKCE only): Notion rejects the
  default registration with a client secret at the token exchange.
- Servers that all accept the same kind of auth can also be given as the standard `mcpServers` dict of Claude Desktop,
  Claude Code and Cursor: `MCPAdapter({"mcpServers": {...}})` (notebook 02).

## 4. Other apps with the API key

Replace the placeholder `<paste SHOP_READ_KEY from .env>` with the value of `SHOP_READ_KEY` from `.env` (or use the
`--public` URL instead of localhost):

- **Claude Code**:
  ```bash
  claude mcp add --transport http shop http://localhost:8001/mcp --header "Authorization: Bearer <paste SHOP_READ_KEY from .env>"
  ```
- **Cursor** (`.cursor/mcp.json`):
  ```json
  { "mcpServers": { "shop": { "url": "http://localhost:8001/mcp",
                              "headers": { "Authorization": "Bearer <paste SHOP_READ_KEY from .env>" } } } }
  ```
- **Claude (claude.ai / Desktop)**: custom connector with the `--public` URL, authentication **No sign-in**, then
  **Request headers** `Authorization: Bearer <key>`. Request headers are in beta for some organizations only.
- Give each person or app its own key so the audit log shows who did what.

**Keep the key out of the config file** (a config you commit or share): reference an environment variable instead,
`$SHOP_READ_KEY` in the `claude mcp add` command, `${SHOP_READ_KEY}` in Claude Code's `.mcp.json`, `${env:SHOP_READ_KEY}`
in Cursor's `mcp.json`. The variable must exist where the app runs; `.env` is read only by this lab's code. Set it in the
terminal first (`export SHOP_READ_KEY=<key>`; PowerShell `$env:SHOP_READ_KEY="<key>"`), then start `claude` or `cursor`
from that terminal. An app started from the Dock / Start menu does not see it: paste the value instead.

## 5. Notion in Claude, Cursor or Claude Code (for comparison)

- Claude: **Customize → Connectors**, search *Notion* (built-in connector) or add a custom connector with
  `https://mcp.notion.com/mcp` and **Sign in when needed**.
- Cursor and Claude Code: `{ "mcpServers": { "notion": { "url": "https://mcp.notion.com/mcp" } } }`; the app opens the
  sign-in itself (Claude Code: `/mcp` → *Authenticate*).

## 6. Extend: other MCP servers

Adding a server is one more entry in the `ClientGroup`, then the agent gets its tools (prefixed with the entry's key):

```python
"linear": Client("https://mcp.linear.app/mcp", auth=OAuth(token_storage=token_store, callback_port=8790)),
"github": Client("https://api.githubcopilot.com/mcp/", auth=os.environ["GITHUB_TOKEN"]),   # personal access token
```

Or, for servers without sign-in, a line in an `mcpServers` dict passed to `MCPAdapter` (notebook 02), the same JSON as
in Claude Desktop, Claude Code or Cursor.

**Sign in without any setup** (`OAuth(...)` or `auth="oauth"`; the client registers itself with Dynamic Client
Registration): Linear `https://mcp.linear.app/mcp`, Atlassian `https://mcp.atlassian.com/v1/mcp`,
Sentry `https://mcp.sentry.dev/mcp`, Canva `https://mcp.canva.com/mcp`, Hugging Face `https://huggingface.co/mcp`,
Stripe `https://mcp.stripe.com`, Vercel `https://mcp.vercel.com`, Supabase `https://mcp.supabase.com/mcp`.

**Need a client you register yourself**:

- **Google Drive** (`https://drivemcp.googleapis.com/mcp/v1`, Workspace developer preview; a personal Gmail account may be
  refused). Google Cloud: create a project, enable the *Google Drive API* and the *Drive MCP API*, set up the OAuth
  consent screen (add yourself as a test user), **Create OAuth client ID → Desktop app**; put the id and secret in
  `.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) and pass them to FastMCP's
  [pre-registered client](https://gofastmcp.com/clients/auth/oauth#pre-registered-clients) option:

  ```python
  drive_auth = OAuth(client_id=os.environ["GOOGLE_CLIENT_ID"], client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
                     scopes=["https://www.googleapis.com/auth/drive.readonly"],
                     token_storage=token_store, callback_port=8790)
  "drive": Client("https://drivemcp.googleapis.com/mcp/v1", auth=drive_auth),
  ```

  Not tested in this lab; two known issues with the current MCP SDK: Google advertises its authorization server as
  `https://accounts.google.com/` while its metadata says issuer `https://accounts.google.com` (the SDK compares them
  exactly and may refuse), and the SDK may replace your `scopes` with every scope the server advertises (8 for Drive).
  Claude's built-in Google Drive connector needs none of this: Anthropic registered its own Google client.
- **GitHub** (`https://api.githubcopilot.com/mcp/`): a GitHub OAuth App (`OAuth(client_id=..., client_secret=...)`), or a
  personal access token as the bearer token (`auth=os.environ["GITHUB_TOKEN"]`).

## Troubleshooting

- `No MCP server at ...`: start the server (step 1); check `SHOP_AUTH_PORT` (and `SHOP_AUTH_MCP_URL`, if set) in `.env`.
- `Missing SHOP_READ_KEY` (or another key): fill it in `.env` (section 0), restart the kernel.
- `SHOP_READ_KEY and SHOP_WRITE_KEY must be different keys`: make a second key for one of them.
- Sign-in never finishes: approve within 5 minutes (FastMCP's default `callback_timeout`), then run the cell again; port 8790 must be free.
- Sign out, or you changed `OAUTH_STORAGE_ENCRYPTION_KEY` (stored tokens can no longer be decrypted): delete `~/.cole-agent/oauth-tokens/`.

## References

- MCP authorization: https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization
- LangChain MCP connections and auth: https://docs.langchain.com/oss/python/langchain/mcp/connections · https://docs.langchain.com/oss/python/langchain/mcp/auth
- FastMCP token verification: https://gofastmcp.com/servers/auth/token-verification · OAuth client: https://gofastmcp.com/clients/auth/oauth
- Claude connectors: https://claude.com/docs/connectors/custom/add-unlisted · Cursor MCP: https://cursor.com/docs/mcp · Claude Code MCP: https://code.claude.com/docs/en/mcp
- Notion MCP: https://developers.notion.com/docs/mcp
- OWASP Logging Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
