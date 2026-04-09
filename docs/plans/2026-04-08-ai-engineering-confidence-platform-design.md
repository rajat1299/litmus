# AI Engineering Confidence Platform Design

**Date:** 2026-04-08  
**Status:** approved design  
**Scope:** venture-scale company framing for Litmus

---

## Goal

Define how Litmus evolves from a grounded verification alpha into a venture-scale product company.

The approved thesis is:

> Litmus should become the confidence layer for AI-native engineering teams.

---

## Design Summary

Litmus should not remain only a deterministic simulation or replay tool.

It should become a full confidence system with three product layers:

1. **Change intelligence** that turns diffs into structured risk objects.
2. **Verification engines** that choose the right evidence-gathering workflow for each risk class.
3. **Confidence control plane** that stores verdicts, policies, gaps, and historical learning and then drives merge and deploy decisions.

---

## Company Shape

The company category is **AI Engineering Confidence Platform**.

The buyer problem is that AI coding increases output faster than review and QA systems can safely absorb. The first wedge is backend and service-layer changes where async, distributed, and failure-path bugs are expensive and hard to see in review.

The product promise is:

**"AI can write the change. Litmus tells you if it is safe to ship."**

---

## Document Set

The detailed company blueprint now lives under `product/company/`:

- `category-definition.md`
- `product-architecture.md`
- `0-to-1-wedge.md`
- `1-to-10-expansion.md`
- `moat-map.md`
- `gtm-and-pricing.md`

These documents intentionally sit outside the grounded alpha docs. They describe the future venture-scale company, not the exact shipped surface of the current repo.

---

## Key Decisions

- Litmus should be positioned as a confidence platform, not only a testing tool.
- The initial wedge remains reliability failures in backend and distributed workflows.
- The expansion path is from local reliability verification into PR trust, policy, and organizational learning.
- The moat should combine verification depth, change intelligence, learning, and workflow ownership.
- The GTM motion should be developer-led with team expansion and light sales assistance.
