# Litmus Alpha Compatibility

This document is the grounded compatibility contract for the current Litmus alpha.

The top-level `README.md` remains aspirational. Use this file when you need the supported launch matrix, the bounded adapter shapes Litmus actually intercepts, and the degradation states that now appear in run artifacts, CLI output, PR comments, replay explanations, and MCP responses.

## Launch Matrix

- Python: `3.11+`
- ASGI app surface: FastAPI / Starlette-style ASGI apps discovered from the current workspace
- HTTP boundary: `httpx` / `aiohttp` through the shipped outbound HTTP simulator
- SQLAlchemy boundary: `sqlalchemy.ext.asyncio` via `create_async_engine` plus either direct `AsyncSession(...)`, `async_sessionmaker`, or `sqlalchemy.orm.sessionmaker(..., class_=AsyncSession)`
- Redis boundary: `redis.asyncio.Redis(...)`, `redis.asyncio.Redis.from_url(...)`, `redis.asyncio.client.Redis(...)`, and `redis.asyncio.client.Redis.from_url(...)`

## Capability States

Litmus now reports the same bounded capability states across verify artifacts and user-facing reporting:

- `supported`: Litmus detected the boundary and successfully intercepted or simulated it on the shipped launch surface
- `unsupported`: Litmus detected the boundary, but the app used an import shape or constructor outside the shipped launch slice
- `detected_only`: Litmus detected the boundary, but no interception or simulation happened
- `not_detected`: Litmus did not observe that boundary in the verified path

## Supported SQLAlchemy Slice

The current SQLAlchemy async launch slice is intentionally narrow:

- `sqlalchemy.ext.asyncio.create_async_engine(...)`
- `sqlalchemy.ext.asyncio.AsyncSession(...)`
- `sqlalchemy.ext.asyncio.async_sessionmaker(...)`
- `sqlalchemy.orm.sessionmaker(..., class_=AsyncSession)`
- single-table primary-key reads and writes that fit the simulator-backed async session contract

Examples outside that slice should degrade as `unsupported` rather than silently claiming full DST coverage.

## Supported Redis Slice

The current Redis async launch slice is intentionally narrow:

- `redis.asyncio.Redis(...)`
- `redis.asyncio.Redis.from_url(...)`
- `redis.asyncio.client.Redis(...)`
- `redis.asyncio.client.Redis.from_url(...)`
- simulator-backed key/value operations exercised through the shipped verify and replay loop

Examples outside that slice should degrade as `unsupported` rather than silently claiming full DST coverage.

## Artifact And Reporting Contract

For every `litmus verify` run:

- `run.json` activity summaries persist a `compatibility` section with the launch matrix and per-boundary capability status
- CLI summaries show a `Compatibility:` section
- PR comments show a `Compatibility` section
- MCP `verify` results return the same structured compatibility payload
- replay explanations append compatibility lines for the boundaries visible in that seed trace
