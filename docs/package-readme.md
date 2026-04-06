# Litmus CLI

Litmus is a grounded alpha for deterministic fault-injection verification of Python async ASGI services.

Install:

```bash
pip install litmus-cli
```

Current grounded alpha surface:

- Python 3.11+
- local CLI: `litmus init`, `litmus verify`, `litmus watch`, `litmus replay`
- local stdio MCP server via `litmus mcp`
- replay over local run artifacts stored under `.litmus/runs/`

Package metadata notes:

- The top-level `README.md` remains aspirational.
- This package readme is the grounded install surface for published releases.
- Homebrew remains deferred.
- Tagged `v*` releases publish through the repository release workflow.
- Manual workflow dispatch defaults to build-only preflight and only publishes when run from a `v*` tag with publish explicitly enabled.

Grounded demo path:

```bash
git clone https://github.com/rajat1299/litmus.git
cd litmus
uv sync --group dev
cd examples/payment_service
uv run --project ../.. litmus verify
uv run --project ../.. litmus replay seed:1
```

The repository `docs/alpha-quickstart.md` file is the detailed source of truth for the current shipped demo and replay flow.
