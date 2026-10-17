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

* **Contracts Precede Code:** All network APIs, shared payloads, and event schemas must be formally defined as contracts before writing application code.
* **End-to-End Type Safety:** Strict typing is enforced everywhere; untyped data structures and dynamic bypasses are banned.
* **Single Source of Truth:** Code stubs, client models, and server handlers derive strictly from the agreed-upon contracts.

### Domain-Driven Design (DDD)

* **Tactical Building Blocks:** Code is structured using explicit DDD constructs: Entities, Value Objects, Aggregates, Domain Services, Repositories, and Domain Events.
* **Identity vs. Value:** Clearly separate entities defined by persistent identity from immutable value objects defined solely by their attributes.
* **Consistency Boundaries:** Aggregates group related entities and value objects to enforce business rules and invariants.
* **Repository Inversion:** Repository interfaces (ports) belong strictly to the domain layer; all database drivers, ORMs, and persistence mechanisms belong to the repository implementations.

### Multi-Layered & Trust-Verified Testing

* **Tiered Test Strategy:** Combine fast, isolated domain tests, realistic integration tests against real ephemeral infrastructure, and full end-to-end flows.
* **Targeted Mutation Testing:** Apply mutation testing specifically to core business logic—tests must fail when domain rules are deliberately broken.
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

* **Strict 4-Tier Architecture:** The codebase is partitioned into Business Modules (`modules/`), Infrastructure Libraries (`libs/`), Executable Elements (`executables/`), and Deployables (`deployables/`).
* **Inert Libraries Core:** Business Modules (`modules/`) hold pure domain and application logic; Infrastructure Libraries (`libs/`) provide shared, cross-cutting technical capabilities. Neither runs on its own.
* **Executable Composition:** Executable Elements (`executables/`) provide concrete runtime drivers (e.g., ConnectRPC API, Cron scheduler, Events listener, AI agent) by importing from `modules/` and `libs/`.
* **Autonomous Deployables:** A Deployable Element (`deployables/`) is a final, standalone runnable unit (e.g., a Docker image or PEX binary) that composes one or more Executable Elements into a single operational package.

### Single-Command Deterministic Verification Gate

* **Zero Manual Verification:** Quality, compliance, and readiness are validated through a single automated command.
* **Unified Pipeline:** Formatting, boundary linting, strict type checks, test suites, and mutation checks run deterministically.
* **Strict Exit-Code Zero:** If any single check fails, the task is incomplete—no exceptions, no manual overrides.

## Product-building process

1. Wireframe folder which is the source-of-truth of the application should look like. It doesn't suppose to have the business logic itself, but it must engage the feel and look of the application, both on mobile and desktop. It's a simple React app. When a new feature needs to be developed and it requires changes in the frontend, it must have first the changes in the wireframe and should be approved by the user.

2. Create a blueprint document for this feature, together with its `.proto` contracts, and get the owner's approval (see [Features Blueprint Document](#features-blueprint-document)).

3. AI agents implements the features according to the blueprint document.


# Features Blueprint Document

Before a feature is built, the agent and the owner discuss it and write down what they agreed in a blueprint. The implementation agent builds exactly what the blueprint says, and nothing it doesn't say.

* **Template:** [`docs/FEATURE_TEMPLATE.md`](docs/FEATURE_TEMPLATE.md)
* **Location:** `docs/<NNN>_FEATURES_<FEATURE_NAME_UPPER_CASE>.md` (e.g., `docs/001_FEATURES_USER_AUTHENTICATION.md`)
* **Collaboration:** the blueprint is written together by a human engineer and an AI agent.
* **Contracts:** the feature's `.proto` files are added in the same pull request as the blueprint.
* **Size:** at most 1,500 lines. A bigger feature is split into smaller features.
* **Living documents:** a blueprint always describes how its feature works today, not only what was decided at the start.

# Framework

## Backend Framework

### Modules

Every business module has the same layout:

```
modules/contacts/
├── domain/         # entities, value objects, aggregates, domain services, repository interfaces, domain events
├── services/       # application services: the module's use cases and its public interface
├── repositories/   # repository implementations and their database tables
└── migrations/     # the module's own database schema
```

* **Domain models are always valid.** Value objects are immutable, and an entity rejects any creation or change that breaks its rules. The domain knows nothing about the database.
* **Domain services** hold business logic that spans several entities and does no I/O. **Application services** load aggregates through repositories, call the domain, save the result, and publish events.
* **Repositories:** the domain declares what it needs from storage, and `repositories/` implements it. A repository loads and saves whole aggregates.
* **Aggregates reference each other by ID**, never through ORM relationships.
* **Only executables import a module**, and only its `services/`.

### Executables

Every executable is one of these five types:

| Executable type | Role |
|---|---|
| **RPC Service** | Serves ConnectRPC requests and returns a response. |
| **Cron Scheduler** | Runs jobs at fixed times or intervals. |
| **Tasks Consumer** | Takes commands from a queue and runs each one exactly once, with retries. |
| **Domain-Events Listener** | Reacts to domain events: facts that already happened in some domain. An event can have any number of listeners, and the publisher does not know them. |
| **AI Agent** | Runs a Pydantic AI agent that users talk to. |

### Deployables

A deployable is a runtime bootstrapper: it lists the executables it runs, creates their infra, and starts them.

[TODO: define how the bootstrapper works in a deployable.]

### Dependency Injection

* Only the deployable creates infra: database pools, HTTP clients, and RPC clients. It passes the instances down to its executables.
* The deployable reads the URIs of databases and of other deployables from environment variables. No other code reads configuration.
* All executables in a deployable share one database pool.
* A client calling a service in the same deployable goes in-process (httpx ASGI transport) instead of over the network.

### `libs/infra`

* Holds the runtime machinery the executables and deployables use, such as the domain-events listener registry. An executable imports it and registers its handlers.
* It is organized by who may import it: `libs/infra/executables/` is imported only by executables, and `libs/infra/deployables/` only by deployables.
* Pants visibility rules enforce this. Importing from the wrong tier fails the verification command.

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

#### Filtering

* **One expressive syntax:** List methods accept filters in [OData](https://docs.oasis-open.org/odata/odata/v4.01/odata-v4.01-part2-url-conventions.html#sec_SystemQueryOptionfilter) syntax, such as `display_name eq 'Avi'`, and the framework turns them into database queries.
* **Explicitly filterable:** each resource declares which fields can be filtered and what each one means in the database. API names may differ from database names. Anything not declared cannot be filtered.
* **Validated before it runs:** an invalid filter is rejected. Agents get an error that tells them how to fix it, and a skill teaches them the syntax.

## Testing

* **Three levels:** unit tests for domain code, component tests for one executable through its contract, and E2E tests for the whole system through the UI.
* **Tests read as scenarios.** Drivers hide how each step is done, so a test shows only what happens.
* **Every external dependency is faked through injection**, using the same bootstrapper as production. No test reaches a real third party.
* **Always tested:** permissions, tenant isolation, full recovery from every failure, and crash recovery.
* **100% coverage, and mutation testing on domain code**, so tests catch real regressions.

## Tech Stack

* Pantsbuild - build system that analyzes fine-grained code dependencies to execute caching, linting, testing, and packaging hermetically at scale (Better than Bazel).

* PostgreSQL - Flexable database with most of the features we expect from database (Transactions, queues, tasks, vector indexing, text search, row-level security, etc...)

* Python in Backend - Everything that we will ever need for the backend (Specificly AI features), will be available in this language.

* Frontend in React + Vite - No need for frontend server since the expectation is that the frontend will be simple and without much of business-logic, everything should be done on the backend and the frontend only display data from backend or send actions to the backend.

* Pydantic AI - Framework for building AI agents, with `pydantic-evals` for measuring their quality.

* Pydantic - Domain models with built-in validation and strict typing.

* SQLModel - ORM for the database tables. Built on Pydantic, like the domain models.

* Firebase authentication - Integrate very easily with the AI, a lot of authentications features are available out of the box, the backend can easily verify the auth JWT from Firebase admin.

* Shadcn - It's has most of the components we will need, very good for building beatiful applications, agents work with it well.

* Copier - Library and command-line utility for rendering projects templates. [TODO: check if i really want to use it] 

## AI Skills and Instructions

### Where Guidelines Live

* **`README.md`** states the principles and describes the framework.
* **`AGENTS.md`** holds the concrete rules that apply to every task.
* **Skills** hold the detail that only some tasks need. Each skill declares when it is used, so nothing has to point to it.
* **A rule that a tool enforces is not written down.** The tool is the rule.
* **Each rule lives in one place** and is never repeated in another.

### Harnesses and Skills

The skills and instructions should be available for the following harnesses:
1. Claude Code
2. Antigravity
3. Pi


The boilerplate will include the following skills:
* Ponytail - Makes your AI agent think like the laziest senior dev in the room. The best code is the code you never wrote.

* shadcn - How to work good with this UI kit.

* ui-ux-pro-max - Has many UI UX examples and can be helpful to find what's a good way to create UI/UX.

* caveman - AI talks too much, let's simplify it.

* api-design - How to design ConnectRPC APIs: the Google AIPs we follow, the Buf style rules, and the patterns we leave out.

### Harness Consistency Check

Every harness must read the same instructions, skills, and subagents. A checker in the verification command fails when they drift apart:

* `CLAUDE.md` is a symbolic link to `AGENTS.md`.
* `.claude/skills` is a symbolic link to `.agents/skills`, which holds the real skill files.
* Every subagent exists in both `.agents/agents/<name>/agent.md` and `.claude/agents/<name>.md`, with the same prompt and front matter. Only the fields each harness defines for itself (`tools`, `subagent`) may differ.
