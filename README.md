# Overview

The goal is to build a boilerplate + framework to build application in the AI area.
Where the guidelines, the process and the structure is defined well for building the system with automnos-AI agents.

## Principles
### Enforced Modular Boundaries

* **Black-Box Isolation:** Modules encapsulate their internal implementation; direct access to private module code is mechanically forbidden.
* **Layered Dependency Direction:** Outer layers depend on inner layers; inner layers never know about or import from outer layers.
* **No Cross-Domain State Mutation:** A module never writes directly to another module's database, tables, or internal state.
* **Autonomous Evolution:** Modules evolve, refactor, and scale independently through explicitly published contracts and asynchronous events.

### Test-Driven Development (TDD)

* **Red-Green-Refactor Loop:** Always write a failing test first, implement the minimum code to pass, then refactor.
* **Zero Untested Production Code:** Never write production logic without a preceding test that defines its intent.
* **Behavior Over Implementation:** Tests verify business outcomes and contracts, not internal implementation trivia.

### Contract-First & Strict Typing

* **Contracts Precede Code:** All network APIs and shared payloads must be formally defined as contracts before writing application code. Domain events are contracts too: typed Pydantic models in the publishing module's domain, which only backend modules consume.
* **End-to-End Type Safety:** Strict typing is enforced everywhere; untyped data structures and dynamic bypasses are banned.
* **Single Source of Truth:** Code stubs, client models, and server handlers derive strictly from the agreed-upon contracts.

### Domain-Driven Design (DDD)

* **Tactical Building Blocks:** Code is structured using explicit DDD constructs: Entities, Value Objects, Aggregates, Domain Services, Repositories, and Domain Events.
* **Identity vs. Value:** Clearly separate entities defined by persistent identity from immutable value objects defined solely by their attributes.
* **Consistency Boundaries:** Aggregates group related entities and value objects to enforce business rules and invariants.
* **Repository Inversion:** Application services depend only on repository interfaces (ports); all database drivers, ORMs, and providers belong to the repository implementations.

### Multi-Layered & Trust-Verified Testing

* **Tiered Test Strategy:** Combine fast, isolated domain tests, realistic integration tests against real ephemeral infrastructure, and full end-to-end flows.
* **No False Confidence:** High line coverage means nothing if assertions are weak—tests must actively catch regressions in business rules.

### Collaborative Blueprinting for Large Features

* **Human-in-the-Loop Alignment:** Large features begin with an iterative design discussion between human and agent to resolve ambiguity before code is written.
* **Collaborative DDD Modeling:** Entities, Value Objects, Aggregates, and boundary definitions must be reviewed and explicitly approved by the human.
* **High-Level Structural Mapping:** Maps the feature across the system layers—which Business Modules handle logic, which Executable Elements run it, and which Deployables host it.
* **High-Leverage Guardrails:** Focuses strictly on architectural boundaries, state transitions, and edge cases where AI typically struggles, avoiding implementation trivia.
* **Deterministic Handoff:** Serves as the authoritative scope contract; if a decision or constraint is not in the blueprint, the implementation agent must not invent it.

### Decoupled Cross-Domain Eventing

* **Asynchronous Notifications:** Cross-domain coordination and reactions are achieved strictly by publishing and subscribing to domain events.
* **Zero Synchronous Write Coupling:** Domains publish events about what occurred; they never orchestrate or reach into other domains' write pipelines.
* **Isolated Failure Domains:** A failure in an event subscriber must never block or roll back the publishing domain's core state transaction.

### Composable 4-Tier Layer Hierarchy

* **Strict 4-Tier Architecture:** The codebase is partitioned into Business Modules (`src/backend/modules/`), Infrastructure Libraries (`src/backend/libs/`), Executable Elements (`src/backend/executables/`), and Deployables (`src/backend/deployables/`).
* **Inert Libraries Core:** Business Modules (`src/backend/modules/`) hold pure domain and application logic; Infrastructure Libraries (`src/backend/libs/`) provide shared, cross-cutting technical capabilities. Neither runs on its own.
* **Executable Composition:** Executable Elements (`src/backend/executables/`) provide concrete runtime drivers (e.g., ConnectRPC API, Cron scheduler, Events listener, AI agent) by importing from `src/backend/modules/` and `src/backend/libs/`.
* **Autonomous Deployables:** A Deployable Element (`src/backend/deployables/`) is a final, standalone runnable unit (e.g., a Docker image or PEX binary) that composes one or more Executable Elements into a single operational package.

### Single-Command Deterministic Verification Gate

* **Zero Manual Verification:** Quality, compliance, and readiness are validated through a single automated command.
* **Unified Pipeline:** Formatting, boundary linting, strict type checks, and test suites run deterministically.
* **Strict Exit-Code Zero:** If any single check fails, the task is incomplete—no exceptions, no manual overrides.

## Product-building process

1. **Wireframe first.** `src/wireframe/` is a simple React app that shows how the product looks and feels on mobile and desktop, without business logic. A feature that changes the UI starts there: the agent maps the user's flow, designs it with the `ui-ux-pro-max` skill, records every decision in `src/wireframe/README.md`, and the owner approves it. The frontend developer designs the states the wireframe leaves out, such as empty lists and errors, and the owner approves them.

2. Create a blueprint document for this feature, together with its `.proto` contracts, and get the owner's approval (see [Features Blueprint Document](#features-blueprint-document)).

3. AI agents implements the features according to the blueprint document.


# Features Blueprint Document

Before a feature is built, the agent and the owner discuss it and write down what they agreed in a blueprint. The implementation agent builds exactly what the blueprint says, and nothing it doesn't say.

* **Template:** [`docs/features/FEATURE_TEMPLATE.md`](docs/features/FEATURE_TEMPLATE.md)
* **Location:** `docs/features/<NNN>_FEATURES_<FEATURE_NAME_UPPER_CASE>.md` (e.g., `docs/features/001_FEATURES_USER_AUTHENTICATION.md`)
* **Collaboration:** the blueprint is written together by a human engineer and an AI agent.
* **Contracts:** the feature's `.proto` files are added in the same pull request as the blueprint.
* **Size:** at most 1,500 lines. A bigger feature is split into smaller features.
* **Living documents:** a blueprint always describes how its feature works today, not only what was decided at the start.

# Framework

## Backend Framework

### Modules

Every business module has the same layout:

```
src/backend/modules/<module>/
├── domain/         # entities, value objects, aggregates, domain services, domain events
├── services/       # application services: the module's use cases and its public interface
├── repositories/   # repository interfaces, and their implementations: database tables, or a provider's API
└── migrations/     # the module's own database schema
```

* **Domain models are always valid.** Value objects are immutable, and an entity rejects any creation or change that breaks its rules. The domain knows nothing about the database.
* **Domain services** hold business logic that spans several entities and does no I/O. **Application services** load aggregates through repositories, call the domain, save the result, and publish events.
* **Repositories:** `repositories/` holds each repository's interface and its implementation, with a database or a provider's API. Application services depend only on the interface. A repository can store its aggregates in Postgres; the users module signs users in through Firebase. A repository loads and saves whole aggregates.
* **Aggregates reference each other by ID**, never through ORM relationships.
* **Modules share only their domain.** A module may import another module's domain, never its services or repositories. Executables and deployables use a module only through its `services/`.

### Executables

Every executable is one of these five types:

| Executable type | Role |
|---|---|
| **RPC Service** | Serves ConnectRPC requests and returns a response. |
| **Cron Scheduler** | Runs jobs at fixed times or intervals. |
| **Tasks Consumer** | Takes commands from a queue and runs each one exactly once, with retries. |
| **Domain-Events Listener** | Reacts to domain events: facts that already happened in some domain. An event can have any number of listeners, and the publisher does not know them. |
| **AI Agent** | Runs a Pydantic AI agent that users talk to. |

An executable is a class. The runtime knows two kinds:

* **HTTP executables** (RPC services and AI agents) give the runtime their routes, which it mounts on the deployable's one HTTP server.
* **Background executables** (cron schedulers, tasks consumers, and domain-events listeners) work outside HTTP. Cron schedulers run today; the other types get their behavior with the first feature that needs them.

Each executable type has its own base class under these two, which holds the wiring every executable of that type shares. `RpcServiceExecutable` mounts one ConnectRPC service and signs in every call. `CronExecutable` holds as many cron jobs as its business area needs. Each executable class names the module schemas it needs migrated, so the runtime migrates them without building it.

### Deployables

A deployable is a list of the executable classes it runs, in one process. The runtime in `src/backend/libs/infra/runtime/` does the rest:

* **Infra, once per process:** it reads the configuration from environment variables and builds the infra every executable shares.
* **Two commands in one image:** `migrate` migrates the schemas of every module the executables use, once per release. `serve` starts all the executables.
* **Health:** `/healthz` answers while the process runs, and `/readyz` answers when the database can be used.
* **Logs:** every log line is one JSON object on stdout, tagged with the ID of the request it served. Each response carries its request ID in `X-Request-ID`.
* **Cron jobs:** the runtime hands every cron job to its cron runner, which decides how jobs are triggered. The first runner runs them inside the process; another runner, such as a hosted scheduler, can replace it without changing the executables.
  [TODO: run each cron job once when a deployable runs more than once. Today every running copy of a deployable runs every job.]
* **Domain events:** a module publishes an event in the same transaction as the change it describes, into one event log in Postgres. The runtime delivers every listener executable's subscriptions from that log: each subscription has its own cursor, receives its event type in order, at least once, and is retried as the subscription's retry strategy says when its handler fails, until the event is parked. Only one running copy of a deployable delivers each subscription. Another bus, such as a hosted broker, can replace the Postgres one without changing listeners.
* **Graceful shutdown:** on SIGTERM, it stops taking new work, lets running work finish, and closes the pools.

### Dependency Injection

* Only the runtime creates infra: the database pool, the clock, and the sign-in service. The runtime builds each executable with it, and the executable takes only what it needs.
* The runtime is the only code that reads configuration, from environment variables.
* All executables in a deployable share one database pool.

### `src/backend/libs/infra`

* Holds the technical capabilities that belong to no business module, such as the database pool and the domain-events bus.
* It is organized by capability: `src/backend/libs/infra/<capability>/`, such as `db/` and `events/`. Each capability folder holds its interface, its provider implementations, and its transport hooks, such as interceptors.
* A capability with business meaning is a module, not a lib. Signing users in belongs to the users module.
* The runtime builds the users module's sign-in service, because every API needs the caller. It is the only lib that uses a module.

### AI Agents

Agents are plain Pydantic AI agents. The framework adds common tools, agent skills, and evals on top of Pydantic AI, without wrapping it.

* **Exposure:** in production, the deployable exposes each agent over the AG-UI protocol. In dev mode, it can also expose each agent through [Pydantic AI's web chat](https://pydantic.dev/docs/ai/guides/web/), which is never exposed in production.
* **`APICall(service, method, params)` tool:** lets an agent call any ConnectRPC method with the signed-in user's credentials, so the agent has exactly the user's permissions. Agents reach modules only through RPC, never through module code directly.
* **RPC agent skill:** Uses the `.proto` contracts. It shows the agent the available services, methods, and parameters, and how to call them with `APICall`.
* **Evals:** every agent has a `pydantic-evals` suite from day one.

### API Design

AIPs define what the API means, and Buf defines how the protos look. Where they overlap, Buf wins, because it is enforced.

* **Semantics follow a subset of [Google AIPs](https://google.aip.dev):** resource-oriented design, standard methods, standard fields and states, pagination, partial updates, soft delete, optimistic concurrency, idempotent requests, and consistent errors. Long-running operations, batch methods, and similar heavy patterns are left out. The API design skill lists the exact AIPs.
* **Form follows the [Buf style guide](https://buf.build/docs/best-practices/style-guide)**, enforced by the verification command.
* **Contracts never break existing clients.** Breaking changes fail the verification command.
* **Generated code is kept apart:** contracts live in `src/protos/`, and the code generated from them lives in `src/generated/<language>/`, one folder per language. Generated code is never edited.

#### Filtering

* **One expressive syntax:** List methods accept filters in [OData](https://docs.oasis-open.org/odata/odata/v4.01/odata-v4.01-part2-url-conventions.html#sec_SystemQueryOptionfilter) syntax, such as `display_name eq 'Avi'`, and the framework turns them into database queries.
* **Explicitly filterable:** each resource declares which fields can be filtered and what each one means in the database. API names may differ from database names. Anything not declared cannot be filtered.
* **Validated before it runs:** an invalid filter is rejected with an error that says what is wrong and lists the filterable fields. The filtering skill teaches agents the syntax.

## Testing

* **Three levels:** unit tests for domain code, component tests for one executable through its contract, and E2E tests for the whole system through the UI.
* **Tests read as scenarios.** Drivers hide how each step is done, so a test shows only what happens.
* **Every external dependency is faked through injection**, using the same runtime as production. No test reaches a real third party.
* **Always tested:** permissions, tenant isolation, full recovery from every failure, and crash recovery.
* **100% coverage with genuine assertions**, so tests catch real regressions.

## Tech Stack

* Pantsbuild - build system that analyzes fine-grained code dependencies to execute caching, linting, testing, and packaging hermetically at scale (Better than Bazel).

* PostgreSQL - Flexable database with most of the features we expect from database (Transactions, queues, tasks, vector indexing, text search, row-level security, etc...)

* Python in Backend - Everything that we will ever need for the backend (Specificly AI features), will be available in this language.

* Frontend in React + Vite - No need for frontend server since the expectation is that the frontend will be simple and without much of business-logic, everything should be done on the backend and the frontend only display data from backend or send actions to the backend.

* Pydantic AI - Framework for building AI agents, with `pydantic-evals` for measuring their quality.

* Pydantic - Domain models with built-in validation and strict typing.

* SQLModel - ORM for the database tables. Built on Pydantic, like the domain models.

* Firebase authentication - Integrate very easily with the AI, a lot of authentications features are available out of the box. The backend verifies Firebase ID tokens itself, with PyJWT and Google's public keys.

* Shadcn - It's has most of the components we will need, very good for building beatiful applications, agents work with it well.

* Git - Projects start as a clone of this repository and take its updates with `git merge`. See [`docs/guides/STARTING_AND_UPDATING_A_PROJECT.md`](docs/guides/STARTING_AND_UPDATING_A_PROJECT.md).

## AI Skills and Instructions

### Where Guidelines Live

* **`README.md`** states the principles and describes the framework.
* **`AGENTS.md`** holds the concrete rules that apply to every task.
* **Skills** hold the detail that only some tasks need. Each skill declares when it is used, so nothing has to point to it.
* **`docs/guides/`** holds the steps for a recurring job that people run, such as starting a project.
* **A rule that a tool enforces is not written down.** The tool is the rule.
* **Each rule lives in one place** and is never repeated in another.

### Harnesses and Skills

The skills and instructions should be available for the following harnesses:
1. Claude Code
2. Antigravity
3. Pi


The boilerplate will include the following plugins:
* [Ponytail](https://github.com/DietrichGebert/ponytail) - Makes your AI agent think like the laziest senior dev in the room. The best code is the code you never wrote.
  * Claude Code and Pi load it from the project settings (`.claude/settings.json` and `.pi/settings.json`).
  * Antigravity has no project-level plugins, so each developer installs it once: `agy plugin install https://github.com/DietrichGebert/ponytail`.

The boilerplate will include the following skills:

* shadcn - How to work good with this UI kit.

* ui-ux-pro-max - Has many UI UX examples and can be helpful to find what's a good way to create UI/UX.

* caveman - AI talks too much, let's simplify it.

* api-design - How to design ConnectRPC APIs: the Google AIPs we follow, the Buf style rules, and the patterns we leave out.

* filtering - The filter syntax List methods accept, and how to make a field filterable.

### Harness Consistency Check

Every harness must read the same instructions, skills, and subagents. A checker in the verification command fails when they drift apart:

* `CLAUDE.md` is a symbolic link to `AGENTS.md`.
* `.claude/skills` is a symbolic link to `.agents/skills`, which holds the real skill files.
* Every subagent exists in both `.agents/agents/<name>/agent.md` and `.claude/agents/<name>.md`, with the same prompt and front matter. Only the fields each harness defines for itself (`tools`, `subagent`) may differ.
