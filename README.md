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
* **Repository Inversion:** Repository interfaces (ports) belong strictly to the domain layer; all database drivers, ORMs, and persistence mechanisms belong to infrastructure adapters.

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
* **Executable Composition:** Executable Elements (`executables/`) provide concrete runtime drivers (e.g., ConnectRPC API, Cron scheduler, Events listener) by importing from `modules/` and `libs/`.
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
* **Approval:** implementation starts only after the owner approves the blueprint.
* **Contracts:** the feature's `.proto` files are added in the same pull request as the blueprint.
* **Size:** at most 1,500 lines. A bigger feature is split into smaller features.

# Framework

## Tech Stack

* Pantsbuild - build system that analyzes fine-grained code dependencies to execute caching, linting, testing, and packaging hermetically at scale (Better than Bazel).

* PostgreSQL - Flexable database with most of the features we expect from database (Transactions, queues, tasks, vector indexing, text search, row-level security, etc...)

* Python in Backend - Everything that we will ever need for the backend (Specificly AI features), will be available in this language.

* Frontend in React + Vite - No need for frontend server since the expectation is that the frontend will be simple and without much of business-logic, everything should be done on the backend and the frontend only display data from backend or send actions to the backend.

* Firebase authentication - Integrate very easily with the AI, a lot of authentications features are available out of the box, the backend can easily verify the auth JWT from Firebase admin.

* Shadcn - It's has most of the components we will need, very good for building beatiful applications, agents work with it well.

## AI Skills

The skills should be available for the following harnesses:
1. Claude Code
2. Antigravity
3. Pi


The boilerplate will include the following skills:
* Ponytail - Makes your AI agent think like the laziest senior dev in the room. The best code is the code you never wrote.

* shadcn - How to work good with this UI kit.

* ui-ux-pro-max - Has many UI UX examples and can be helpful to find what's a good way to create UI/UX.

* caveman - AI talks too much, let's simplify it.
