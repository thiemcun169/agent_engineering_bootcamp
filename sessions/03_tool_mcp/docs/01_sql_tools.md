# Part 1 · SQL tools for an agent

**What you do**: write three read-only tools over the shop database and give them to a `create_agent` agent. You see how
the model chooses a tool, calls it and uses the result, fixes a wrong column from the error message, and cannot write.

| Tool | Arguments | Returns |
|---|---|---|
| `list_tables()` | none | table names |
| `describe_table(table)` | a table name | columns + 3 sample rows |
| `run_query(sql)` | one `SELECT` | at most 50 rows (`note` when cut) |

## 0. `.env`
Needs `OPENAI_API_KEY` (and optionally `MODEL`) in `.env`: [README, setup step 3](../README.md#3-set-up-env).

## Run
No server is needed: the tools run inside the notebook.
1. Open `notebooks/01_sql_tools_agent.ipynb`, kernel **venvAE03** (README, setup step 4).
2. Run the cells in order. The demo cell sets `question = "..."`: edit it to ask your own question and run it again.
3. The answer **streams**: one line per tool call (`→ run_query({...})`) and result (`← run_query success: ...`), then
   the answer token by token. `INFO | run_query("SELECT …") -> ok 1 ms` lines are the tools' log (diagnostics): one
   line per tool call, `ok` or `error`, and the time it took.

The wrong-column cell (real run): the first `run_query` returns the error with the valid columns, the model rewrites the
query and the second call succeeds.

```text
→ run_query({"sql": "SELECT SUM(total_amount) FROM orders WHERE status = 'delivered' AND created_at LIKE '2026-09%'"})
INFO | run_query("SELECT SUM(total_amount) FROM orders WHERE status = 'delivered' AND c…) -> error 0 ms
← run_query error: no such column: total_amount. Valid columns: customers(id, name, email, city, created_at); order_items(order_i…
→ describe_table({"table": "order_items"})
INFO | describe_table('order_items') -> ok 0 ms
← describe_table success: {"table": "order_items", "columns": [{"name": "order_id", "type": "INTEGER"}, …
→ run_query({"sql": "SELECT SUM(oi.quantity * oi.unit_price) AS delivered_revenue_vnd FROM orders o JOIN order_items oi ON…)
INFO | run_query("SELECT SUM(oi.quantity * oi.unit_price) AS delivered_revenue_vnd FROM…) -> ok 3 ms
← run_query success: {"rows": [{"delivered_revenue_vnd": 315880500}], "row_count": 1}
The query failed because `orders` has no `total_amount` column. Summing `quantity × unit_price` for delivered
September 2026 orders gives **315,880,500 VND**.
```

## The data
`data/shop.db`, built by `data/seed_shop.py` (same data every run): 200 customers in Vietnamese cities, 40 products in
4 categories (Books, Electronics, Home, Toys), 1,500 orders from January to September 2026, prices in VND.

| Table | Columns |
|---|---|
| `customers` | `id, name, email, city, created_at` |
| `products` | `id, name, category, price` |
| `orders` | `id, customer_id, status` (`pending, paid, shipped, delivered, cancelled`), `created_at` |
| `order_items` | `order_id, product_id, quantity, unit_price` |

## References
- Tools: https://docs.langchain.com/oss/python/langchain/tools
- SQL agent: https://docs.langchain.com/oss/python/langchain/sql-agent
- Writing tools for agents: https://www.anthropic.com/engineering/writing-tools-for-agents
