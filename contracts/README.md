# Draft interface contracts

These files describe this repository's own data structures. They are not native iBlueprint imports or WaerLinx/NetSuite API contracts.

`openapi.json` lists local HTTP endpoints and request schemas. Generate it and the smaller JSON Schemas with:

```bash
python scripts/export_contracts.py
python scripts/export_contracts.py --check
```

`receipt-input` permits incomplete drafts. The application enforces stricter checks before review, approval and handoff; schema validation alone does not establish readiness. Decimal amounts serialize as strings to preserve receiving precision. `neutral-handoff` describes the approved payload for the mock adapter. It requires an existing purchase-order reference and cannot create items or purchase orders.

`model-output` accepts a catalog suggestion only. There are no fields for inventory writes, approval, quantity, weight or food-safety decisions. Output is revalidated against the permitted catalog before it reaches the UI.

The browser interface uses the same-origin API with a bearer token from a selectable demo identity. This demonstrates role boundaries but is not real authentication. Interactive Swagger/ReDoc pages are disabled because this draft uses no CDN assets; `/openapi.json` remains available.
