# RockSolid

RockSolid is a framework for building a product with AI agents: a Python backend and the clients that call it, joined by ConnectRPC contracts. It brings the guidelines (`AGENTS.md`), the skills, the tooling, and the shared libraries, so autonomous agents build every product to one standard.

## Who Uses It

Teams that build a product with AI agents. A project starts as a clone of RockSolid, keeps its git history, and takes RockSolid's updates with `git merge`.

## How It Works

- **The framework:** its principles, its backend tiers, the process from wireframe to blueprint to code, and how it is tested are described in [`.agents/skills/rocksolid/FRAMEWORK.md`](.agents/skills/rocksolid/FRAMEWORK.md).
- **Building each piece:** the `rocksolid` skill shows each backend piece built, with working examples in `.agents/skills/rocksolid/examples/`.
- **Starting and updating a project:** [`docs/guides/STARTING_AND_UPDATING_A_PROJECT.md`](docs/guides/STARTING_AND_UPDATING_A_PROJECT.md). A project replaces this file with its product's own README.

## Run It

- `make dev` runs the whole system on this machine: Postgres in Docker, the backend, and the frontend.
- `make verify` runs every check; a change is done only when it passes.
- `make verify-examples` runs the same checks with the skill's examples in place. Only RockSolid runs it.
