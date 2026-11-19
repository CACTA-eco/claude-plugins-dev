# Contributing

Issues are welcome: bug reports, suggestions and questions about the plugins in this registry.

## Pull requests

Everything under `plugins/` is generated from a private Cacta repository and synced here
one-way by CI. Edits made here are overwritten on the next sync, so **PRs that touch
`plugins/` are not merged**. If a change looks good, maintainers will port it manually
upstream and it will arrive here through the next sync.

PRs that only touch repository files outside `plugins/` (README, workflows, templates)
are fine.

Before opening a PR, run `claude plugin validate .`.
