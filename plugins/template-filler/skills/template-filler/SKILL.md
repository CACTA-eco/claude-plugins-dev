---
name: template-filler
description: Fill Cacta bulk-import templates (nodes, catalog entries, observations) from the user's source data. Use when the user wants to load, import or convert data for the Cacta platform. PLACEHOLDER - overwritten by CI.
---
<!-- GENERATED FILE: this file is synced from a private Cacta repository. Do not edit it here; any changes will be overwritten by the next sync. -->

# Template filler (placeholder)

> **This is a placeholder.** The real skill content is synced here by CI from a
> private repository and will overwrite this file.

## Required tools

This skill uses tools from a Cacta-compatible MCP server. Refer to them by bare name only:

- `generate_node_bulk_excel`
- `generate_catalog_bulk_excel`
- `generate_observation_bulk_excel`

## Fallback

If these tools are not available in this session, tell the user to connect a
compatible MCP server (see the plugin README for `CACTA_MCP_URL` and
`CACTA_MCP_TOKEN`) and stop. Do not attempt the task without the tools.

## Workflow

1. Call the relevant `generate_*` tool without rows to get the blank template.
2. Map the user's source data onto it.
3. Hand the completed file back to the user, who uploads it manually.
