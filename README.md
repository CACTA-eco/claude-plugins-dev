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
| `template-filler` | 0.1.6 | Fill Cacta bulk-import templates from your source data using the Cacta MCP server. |

## MCP server

The plugin connects to a server named `cacta` at
`https://mcp.dev.cacta.eco/nodal-db/mcp`. Authentication is handled by Claude
(OAuth) when you connect; no environment variables are needed.

To use a different server, edit the `url` in `plugins/template-filler/.mcp.json`.

## License

[MIT](LICENSE)
