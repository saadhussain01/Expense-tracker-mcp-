# ExpenseTracker MCP Server

A FastMCP server that tracks personal expenses via SQLite, deployable to Prefect Horizon.

## Tools

| Tool | Description |
|---|---|
| `add_expense` | Add a new expense (date, amount, category, optional subcategory/note) |
| `list_expenses` | List expenses between two dates |
| `summarize` | Summarize totals by category between two dates |

## Resource

- `expense:///categories` — JSON list of available categories

## Local Development

```bash
pip install fastmcp aiosqlite
fastmcp inspect server.py:mcp   # verify tools are visible
fastmcp run server.py:mcp       # run locally
```

## Deploy to Horizon

See the step-by-step guide below or visit https://horizon.prefect.io
