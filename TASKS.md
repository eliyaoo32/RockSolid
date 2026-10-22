# Tasks

- [-] Take inspirations and ideas from [peva3/anchor](https://github.com/peva3/anchor)

- [x] Repository foundation
    - [x] Create modules, libs, executables, deployables folders
    - [x] Run local Postgres with Docker Compose

- [ ] Pants setup
    - [x] Enable Pants Python, Ruff, and Pyright backends
    - [x] Enable the Pants visibility backend
    - [x] Pin the Python version and lock dependencies
    - [x] Add a Pants verify alias for all goals
    - [x] Add a Makefile verifying the backend and contracts
    - [x] Add the frontend checks to make verify
    - [x] Write Pants visibility rules for the tiers
    - [x] Forbid ORM imports in module domain code
    - [ ] Port blueprint docs checker from EasyTivuch
    - [x] Add GitHub Actions workflow running verify

- [ ] Contracts
    - [x] Lint and format contracts with buf in make verify
    - [x] Add Buf breaking-change detection to verify
    - [x] Generate and commit ConnectRPC code with buf
    - [x] Fail verify when generated code is stale
    - [x] Generate TypeScript client from protos
    - [ ] Validate requests with buf.validate

- [x] Database
    - [x] Add Postgres connection pool to src/backend/libs/infra
    - [x] Add database migrations per module
    - [x] Give each module its own database schema

- [x] Filtering
    - [x] Wrap odata-query in src/backend/libs/infra/filtering
    - [x] Map filterable API paths to SQL expressions
    - [x] Validate filters for syntax, paths, and types
    - [x] Write the filtering syntax agent skill

- [ ] Executable runtimes in src/backend/libs/infra
    - [x] Build the ConnectRPC service runtime
    - [x] Build the cron scheduler runtime
    - [ ] TODO: run each cron job once across replicas
    - [x] Build the tasks queue on Postgres
    - [x] Build the domain events bus on Postgres
    - [ ] TODO: clean up old events in the event log
    - [x] Build the AI agent runtime with Pydantic AI
    - [ ] TODO: delete old conversations
    - [ ] TODO: trim conversations that outgrow the model's context

- [ ] AI agent framework
    - [x] Expose agents over AG-UI in deployables
    - [x] Expose agent web chat in debug mode
    - [x] Keep agent conversations on the server
    - [x] Run agent tools as the signed-in user
    - [x] Test agents with Pydantic AI's FunctionModel
    - [ ] TODO: set up pydantic-evals suites for agents
    - [ ] TODO: run agent evals in a separate GitHub Action

- [x] Deployables
    - [x] Define how the bootstrapper works
    - [x] Build the generic deployable bootstrapper
    - [x] Decide how deployables load and validate configuration
    - [x] Load deployable config from environment variables
    - [x] Handle graceful startup and shutdown
    - [x] Package each deployable as a Docker image

- [x] Authentication
    - [x] Verify Firebase JWT in RPC endpoints
    - [x] Verify Firebase JWT in AG-UI endpoints
    - [x] Add Firebase sign-in to the frontend

- [ ] Frontend
    - [x] Scaffold React and Vite app with shadcn
    - [x] Scaffold the wireframe React app
    - [x] Call the backend through the generated client
    - [ ] Choose a frontend AG-UI client library
    - [ ] Connect the frontend to agents over AG-UI

- [ ] Testing infra
    - [x] Run ephemeral Postgres in tests with testcontainers
    - [x] Boot executables in tests with injected fakes
    - [ ] Build a fake RPC service for tests
    - [ ] Replay recorded third-party HTTP responses
    - [x] Build fake third-party servers for E2E
    - [x] Build a fake Firebase token verifier
    - [x] Sign E2E users in with the backend's debug user
    - [x] Answer E2E agents from a fake Ollama server
    - [x] Add an injectable clock
    - [x] Add an eventually helper for async effects
    - [x] Restrict src/backend/libs/testing to test code
    - [x] Set up the E2E package with Playwright

- [ ] Contacts example
    - [x] Build Clients CRUD across all tiers
    - [x] Build a clients assistant agent
    - [ ] TODO: add evals to the clients assistant

- [ ] AI instructions and skills (for Claude Code, Antigravity, Pi)
    - [x] Write AGENTS.md with structure and guidelines
    - [ ] Port harness consistency checker from EasyTivuch
    - [ ] Add a skill for writing blueprints
    - [x] Add an API design skill (AIPs and Buf)
    - [x] Link .claude/skills to .agents/skills
    - [x] Install the Ponytail plugin
    - [x] Install the shadcn skill
    - [x] Install the ui-ux-pro-max skill
    - [x] Install the caveman skill
    - [x] Install Emil Kowalski's skills
    - [x] Install the Taste Skill
    - [ ] Write guidelines in AGENTS.md for when to use each skill
    - [ ] Find a skill for Domain Driven Design.

- [x] Project template
    - [x] Start projects as a git clone, not Copier
    - [x] Document creating a new project from RockSolid
    - [x] Document updating a project to new RockSolid versions
