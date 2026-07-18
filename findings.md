# Findings

## Project
- Python local coding agent with Textual TUI, tool calling, permissions, sessions, context compaction, provider adapters, tests, and benchmarks.
- Public-facing current name is AgentLens; internal package and CLI are `firstcoder`.
- Existing `task_plan.md` documents an earlier Windows IME compatibility change and should remain as project history unless it contains stale branding references.

## GitHub / Git
- `d:\桌面\实习\AgentLens` is not currently a Git repository.
- `gh` CLI is unavailable.
- Git global identity is configured as `mgh-666 <3203314349@qq.com>`.
- User supplied organization URL: https://github.com/explore-ai-dev/

## Naming
- Chosen public name: AgentLens.
- Rationale: the project makes coding-agent internals visible and inspectable; “Lens” communicates observability/learning better than a generic “Coder” name.

## Branding scope
- Replace public prose headings, image alt text, project comparison table labels, docs references, and DeepWiki/source repository links where they are explicitly branding.
- Preserve internal package directory, import paths, executable name, environment variable names, config paths, benchmark adapter module paths, and command examples unless the user later explicitly requests a breaking rename.
