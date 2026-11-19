# Cacta Claude plugins

A public [Claude plugin marketplace](https://code.claude.com/docs/en/plugins/create-marketplace)
(a "registry") for plugins published by Cacta.

> **This repository is generated.** The contents of `plugins/` are synced one-way by CI
> from a private development repository. Do not edit them by hand; changes are
> overwritten. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Install

### claude.ai / Claude Desktop

Customize → Plugins → **+** → Add marketplace → Add from a repository →
`CACTA-eco/claude-plugins`

### Claude Code

```
/plugin marketplace add CACTA-eco/claude-plugins
/plugin install template-filler@cacta
```

## Plugins

| Plugin | Version | Description |
|---|---|---|
| `template-filler` | 0.1.0 | Fill Cacta bulk-import templates from your source data using the Cacta MCP server. |

## Using a different MCP server

The plugin connects to a server named `cacta` whose URL and credentials come from
environment variables, set before starting Claude Code:

| Variable | Purpose |
|---|---|
| `CACTA_MCP_URL` | MCP server URL. Defaults to the Cacta server configured in `.mcp.json`. |
| `CACTA_MCP_TOKEN` | Bearer token sent in the `Authorization` header. |

```bash
export CACTA_MCP_URL="https://mcp.example.com/mcp"
export CACTA_MCP_TOKEN="..."
```

## License

[MIT](LICENSE)
