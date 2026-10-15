# Documentation

## Using Substrakt

- [Getting started](getting-started.md): installation with `npm start`, WSL2, first steps
- [Configuration](configuration.md): operating modes, policy file, directories, environment
- [Document types](document-types.md): describing a kind of document in YAML

## Understanding and changing it

- [Architecture](architecture/README.md): three processes, egress chokepoint, persistence boundary; diagram as [SVG](architecture/architecture.svg) with [Mermaid source](architecture/architecture.mmd)
- [Development](development.md): commands, project layout, tests, glossary
- [Gates](gates.md): what CI rejects and why
- [Contributing](../CONTRIBUTING.md) and [Security policy](../SECURITY.md)
- [Changelog](../CHANGELOG.md)
- [Release readiness](release-readiness.md): licence, history and data check before going public

## Records

- [`decisions.md`](decisions.md): binding decisions, condensed
- [`status.md`](status.md): report after stage 1; its lessons on CI, first start and wrong assumptions still apply
- [`design/design-language.md`](design/design-language.md): design language v2 with a reference prototype
- [`measurements/`](measurements/): measurement protocols from `bench/`
- [`harness/`](harness/): rules for coding agents, loaded by `CLAUDE.md`
- [`plans/`](plans/): hand-over plans for coding agents

The original analyses behind the decisions (technical evaluation, licence
audit, inference architecture, build brief) are internal documents and not
published. `decisions.md` holds what is binding from them; what is
enforced by machine is in [`../licenses/policy.toml`](../licenses/policy.toml),
not in prose.
