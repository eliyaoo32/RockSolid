# Tasks

- [-] Take inspirations and ideas from [peva3/anchor](https://github.com/peva3/anchor)

- [ ] Repository foundation
    - [ ] Create modules, libs, executables, deployables folders
    - [ ] Run local Postgres with Docker Compose

- [ ] Pants setup
    - [ ] Enable Pants Python, Ruff, Pyright, visibility backends
    - [ ] Pin the Python version and lock dependencies
    - [ ] Add a Pants verify alias for all goals
    - [ ] Add a Makefile verifying backend and frontend
    - [ ] Write Pants visibility rules for the tiers
    - [ ] Forbid ORM imports in module domain code
    - [ ] Add mutation testing for domain code
    - [ ] Port blueprint docs checker from EasyTivuch
    - [ ] Add GitHub Actions workflow running verify

- [ ] Contracts
    - [ ] Enable the Pants Buf lint backend
    - [ ] Add Buf breaking-change detection to verify
    - [ ] Generate and commit ConnectRPC code with buf
    - [ ] Fail verify when generated code is stale
    - [ ] Generate TypeScript client from protos
    - [ ] Validate requests with buf.validate

- [ ] Database
    - [ ] Add Postgres connection pool to libs/infra
    - [ ] Add database migrations per module
    - [ ] Give each module its own database schema

- [ ] Filtering
    - [ ] Wrap odata-query behind a libs/infra interface
    - [ ] Map filterable API paths to SQL expressions
    - [ ] Validate filters for syntax, paths, and types
    - [ ] Write the filtering syntax agent skill

- [ ] Executable runtimes in libs/infra
    - [ ] Build the ConnectRPC service runtime
    - [ ] Build the cron scheduler runtime
    - [ ] Build the tasks queue on Postgres
    - [ ] Build the domain events bus on Postgres
    - [ ] Build the AI agent runtime with Pydantic AI

- [ ] AI agent framework
    - [ ] Expose agents over AG-UI in deployables
    - [ ] Expose agent web chat in dev mode
    - [ ] Build the APICall tool for ConnectRPC methods
    - [ ] Run APICall with the signed-in user's credentials
    - [ ] Generate the RPC agent skill from protos
    - [ ] Test agents with Pydantic AI's TestModel
    - [ ] Set up pydantic-evals suites for agents
    - [ ] Run agent evals in a separate GitHub Action

- [ ] Deployables
    - [ ] Define how the bootstrapper works
    - [ ] Build the generic deployable bootstrapper
    - [ ] Decide how deployables load and validate configuration
    - [ ] Load deployable config from environment variables
    - [ ] Handle graceful startup and shutdown
    - [ ] Package each deployable as a Docker image

- [ ] Authentication
    - [ ] Verify Firebase JWT in RPC and AG-UI endpoints
    - [ ] Add Firebase sign-in to the frontend

- [ ] Frontend
    - [ ] Scaffold React and Vite app with shadcn
    - [ ] Scaffold the wireframe React app
    - [ ] Call the backend through the generated client
    - [ ] Choose a frontend AG-UI client library
    - [ ] Connect the frontend to agents over AG-UI

- [ ] Testing infra
    - [ ] Run ephemeral Postgres in tests with testcontainers
    - [ ] Boot executables in tests with injected fakes
    - [ ] Build a fake RPC service for tests
    - [ ] Replay recorded third-party HTTP responses
    - [ ] Build fake third-party servers for E2E
    - [ ] Build a fake Firebase token verifier
    - [ ] Run the Firebase Auth emulator in E2E
    - [ ] Select the test LLM through an environment variable
    - [ ] Add an injectable clock
    - [ ] Add an eventually helper for async effects
    - [ ] Restrict libs/testing to test code
    - [ ] Set up the E2E package with Playwright

- [ ] Contacts example
    - [ ] Build Contacts CRUD across all tiers
    - [ ] Build a Contacts assistant agent with evals

- [ ] AI instructions and skills (for Claude Code, Antigravity, Pi)
    - [ ] Write AGENTS.md with structure and guidelines
    - [ ] Port harness consistency checker from EasyTivuch
    - [ ] Add a skill for writing blueprints
    - [x] Add an API design skill (AIPs and Buf)
    - [x] Link .claude/skills to .agents/skills
    - [x] Install the Ponytail plugin
    - [ ] Install the shadcn skill
    - [ ] Install the ui-ux-pro-max skill
    - [ ] Install the caveman skill
    - [ ] Find a skill for Domain Driven Design.

- [ ] Project template
    - [ ] Decide whether to use Copier
    - [ ] Document creating a new project from RockSolid
    - [ ] Document updating a project to new RockSolid versions
