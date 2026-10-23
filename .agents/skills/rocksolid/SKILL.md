---
name: rocksolid
description: How to build each piece of a product on RockSolid, the framework for products made of a backend and the clients that call it, with a working example of each. Use for questions about RockSolid's principles, process, and design, and when adding a Python dependency or a contract module, or when creating or changing a module, an entity, a repository, a migration, a domain event, a task, an executable (RPC service, AI agent, cron scheduler, tasks consumer, or domain-events listener), a deployable, or their component and E2E tests.
---

# RockSolid

RockSolid is a framework for building a product with AI agents: a Python backend and the clients that call it, joined by ConnectRPC contracts.

- **Backend:** business modules, executables (RPC services, AI agents, cron schedulers, tasks consumers, and domain-events listeners), and the deployables that run them, on shared infrastructure libraries.
- **Clients:** the React web app in `src/clients/web-app/`, which calls the backend only through clients generated from the contracts, and the wireframe in `src/clients/wireframe/`, which holds the approved design.
- **Contracts:** `.proto` files in `src/protos/`, from which the backend's services and every client's calls are generated.
- **Tests and tooling:** unit, component, and E2E tests at 100% coverage, and one verification command, `make verify`.

[`FRAMEWORK.md`](FRAMEWORK.md), next to this file, states RockSolid's principles and explains each part and why it is built that way. `AGENTS.md` holds the rules every change follows. This skill says how to build each backend piece and its tests, and shows them built.

## Examples

`examples/src/` mirrors `src/`: each file sits at the path it would have in a project. Together they build one feature, clients, through every tier. Before building a piece, read its example and follow it. Copy what fits into `src/` under your own names; never import from the skill.

| Piece | Example |
|---|---|
| Entity and its unit test | `examples/src/backend/modules/clients/domain/client.py`, `client_test.py` |
| Domain event | `examples/src/backend/modules/clients/domain/client_events.py` |
| Task | `examples/src/backend/modules/clients/domain/client_tasks.py` |
| Repository, table model, and filter schema | `examples/src/backend/modules/clients/repositories/` |
| Application service that publishes events and queues tasks | `examples/src/backend/modules/clients/services/clients.py`, `setup.py` |
| The module's errors | `examples/src/backend/modules/clients/services/errors.py` |
| Module settings, and a third party the module talks to | `ClientsSettings` in `examples/src/backend/modules/clients/services/setup.py`, `examples/src/backend/modules/clients/repositories/mail_api_clients.py`, and its fake, `examples/src/tests/e2e/framework/fakes/mail_api.py` |
| Module schema migrations | `examples/src/backend/modules/clients/migrations/` |
| Contract | `examples/src/protos/clients/v1/clients.proto` |
| RPC service | `examples/src/backend/executables/clients_api/` |
| AI agent | `examples/src/backend/executables/clients_assistant/` |
| Cron scheduler | `examples/src/backend/executables/clients_digest/` |
| Domain-events listener | `examples/src/backend/executables/client_activity/` |
| Tasks consumer | `examples/src/backend/executables/client_welcome/` |
| Component tests, with their driver and fixtures | each executable's `tests/` |
| Deployable | `examples/src/backend/deployables/examples/main.py` |
| E2E test of an agent | `examples/src/tests/e2e/clients_assistant_test.py`, with `examples/src/tests/e2e/framework/agents.py`, which a project with an agent copies into `src/tests/e2e/framework/` |

RockSolid's CI verifies the examples with `make verify-examples`: it copies them into a throwaway copy of the repository and runs `make verify` there. An example only adds files. A change to the framework that breaks an example fixes the example in the same pull request.

## Dependencies
- **Through Pants Only:** Add the requirement to `3rdparty/python/requirements.txt`, then run `pants generate-lockfiles`. Pants infers which code uses it. Never install with `pip` or `uv`; Pants does not read their environments or lockfiles.
- **Our Packages Are Listed for Ruff:** `known-first-party` in `pyproject.toml` lists every top-level Python package of our own: each folder in `src/backend/` and `src/tests/`, and each module generated into `src/generated/python/`. Pants lints a few files at a time, so Ruff cannot find our packages on disk and sorts an unlisted one as third-party. A change that adds such a folder or a contract module (`src/protos/<module>/`) adds its name to the list.

## Repositories
- **Repository Files:** A repository's interface and its implementation both live in `repositories/`, in separate files: `<aggregate>_repository.py` for the interface and `postgres_<aggregates>.py` for a Postgres implementation. Application services import only the interface; only the module's `services/setup.py` imports an implementation. The implementation talks to a database, or to a provider's API as `firebase_users.py` does to sign users in. A database repository uses SQLModel table models (`table=True`). It converts with `model_validate` (`<Entity>.model_validate(row, from_attributes=True)` and `<Entity>Row.model_validate(entity)`), and maps by hand only the fields whose name or shape differ, such as value-object columns.
- **Value Objects Are Prefixed Columns:** In the database, a value object's fields are columns prefixed with the name of the entity field that holds it (`address_city`, `address_street`). The repository maps them.
- **Errors Live in the Service Layer:** A module's errors are defined only in its `services/errors.py`. A repository raises them from there, such as `MailNotConfiguredError` in `mail_api_clients.py`, and executables import them from there to map them to a Connect code or `NonRetryableError`. Never define an error in `domain/` or `repositories/`, and never re-export one.

## Executables
- **An Executable Is a Class:** An executable subclasses the base class of its type, such as `RpcServiceExecutable`, declares its `migrations`, and implements only what differs from other executables of its type. Wiring that every executable of a type repeats belongs in the type's base class.
- **Cron Jobs:** A cron executable subclasses `CronExecutable` and returns its jobs from `jobs()`, each a `CronJob(schedule, function)` with a UTC cron expression such as `*/5 * * * *`. The executable alone decides its jobs; group them into executables by business area. A job never schedules itself, sleeps, or loops: the runtime's cron runner triggers it. A job that fails is logged and runs again at its next time.
- **Domain Events:** A domain event is a frozen Pydantic model in the publishing module's `domain/`, with a class-level `event_type` of the form `"<module>.<EventClassName>"`. Name it in the past tense, after the fact it records. The event log stores `event_type`, so it never changes; fields are only added, with defaults, so events already in the log still load.
- **The Service Publishes and Queues:** Which events a change publishes and which tasks it queues is service logic, so the application service creates them and writes them itself, with `append_events` and `enqueue_tasks`. It writes them in a function it passes to the repository's `save` as `before_commit`; the repository runs that function in the save's transaction and never creates, publishes, or queues anything itself.
- **Listening:** A listener executable subclasses `DomainEventsListenerExecutable` and returns `Subscription(name, event_class, handler)` from `subscriptions()`. The name keeps the subscription's place in the event log, so it stays the same across releases. A subscription's `retry` strategy, from `src/backend/libs/infra/retry/` (`Exponential` by default, `Constant`, `Delays`, or `NO_RETRY`), says how a failing handler is retried before its event is parked. A handler raises `NonRetryableError` for a failure that trying again cannot fix, and its event is parked at once.
- **Tasks:** A task is a frozen Pydantic model in the module's `domain/` that asks for work, with a class-level `task_type` of the form `"<module>.<TaskClassName>"`. Name it in the imperative, after the work it asks for. The queue stores `task_type`, so it never changes; fields are only added, with defaults, so tasks already in the queue still load.
- **Recurring Tasks:** Work that recurs, such as every two hours, is a cron job that queues a task.
- **Consuming:** A consumer executable subclasses `TasksConsumerExecutable` and returns `TaskHandler(task_class, handler)` from `handlers()`. Each task type has exactly one handler across all deployables. A handler's `retry` strategy and `NonRetryableError` work as they do for subscriptions, and a task that stops retrying is parked.
- **Agent Executables:** An AI agent is a class that subclasses `AgentExecutable` and has three things:
  - `name`: the agent answers at `/agents/<name>`, and its users' conversations are stored under this name. Never rename it, or its users lose their conversations.
  - `require_auth`: `True` when only signed-in users may talk to the agent.
  - `agent()`: a method that builds and returns the Pydantic AI `Agent`, with its instructions and tools. It picks its model with `self.infra.models`, such as `self.infra.models.ollama(MODEL)`, where `MODEL` is a constant at the top of the file.

## Deployables
- **A Deployable Is a List:** A deployable's `main.py` lists its executable classes and hands them to the runtime's `run`. It builds nothing itself. The framework's deployable is `app`, which runs every executable in one process; a new executable is added to its list. A project that splits its executables into several deployables names each after its role, such as `api` or `workers`.
- **Migrate, Then Serve:** The image runs `migrate` once per release and `serve` on every replica. `serve` never migrates.

## Tests

### Test Folders
```
src/backend/modules/<module>/domain/<entity>.py
src/backend/modules/<module>/domain/<entity>_test.py          # unit test, next to its source
src/backend/executables/<name>/tests/<feature>_test.py       # component tests, named after the feature
src/backend/executables/<name>/tests/framework/               # this executable's drivers, fixtures, and fakes
src/backend/libs/testing/                                     # fakes and helpers shared by several executables
src/clients/web-app/tests/framework/                          # the frontend's drivers, fakes, and test setup
src/clients/web-app/src/<file>.test.tsx                       # frontend unit test, next to its source
src/tests/e2e/<feature>_test.py                               # E2E tests, named after the feature
src/tests/e2e/framework/                                      # the running system and the E2E driver
src/tests/e2e/framework/fakes/<third_party>.py                # a fake server for each third party
```
- Drivers, fixtures, and fakes live only in `framework/` folders or `src/backend/libs/testing/`, never in test files or product code.
- A fake of a third party is a server in `src/tests/e2e/framework/fakes/`, one file named after the third party (`fakes/ollama.py`), with its committed responses in `fakes/testdata/`. It exports `serve()`, which runs it and gives the settings that point the deployables at it (`environment`). The E2E system starts every fake it finds there and passes their settings to every deployable; a component test starts the fake it needs and sets its settings.
- Only test code may import `src/backend/libs/testing/`.

### Drivers
- **Driver Pattern:** Component and E2E tests read as scenarios. A driver hides how each step is done: `driver.when.*` performs actions, and `driver.get.*` reads results.
  ```python
  driver.when.create_record(name="Avi", email="avi@example.com")
  driver.when.rename_record(name="Avi Cohen")
  assert driver.get.record().name == "Avi Cohen"
  ```

### Fakes and Test Infrastructure
- **Production Runtime:** Tests run executables with `run_executables(...)` from `src/backend/libs/testing/runtime.py`. It runs them through the real runtime, with fakes in place of the outside world and `FakeTime` driving cron jobs and event and task retries, so the tests exercise the real wiring. An executable's fixture adds only what is its own, such as its tables and its fake sign-in.
- **Time Moves Only When a Test Moves It:** Tests use `FakeTime` from `src/backend/libs/testing/time.py` as the clock, and move it with `advance`. Passed as a cron runner's wait (`InProcessCronRunner(time, time.wait)`), it makes a job run exactly when the test moves time past its schedule.

| Dependency | Component tests | E2E tests |
|---|---|---|
| Database | Real ephemeral Postgres (testcontainers); each test starts from empty tables | Real ephemeral Postgres |
| Other RPC services | A fake implementation of the generated service, served by a local test server | The real deployable, or the same fake |
| Third-party APIs | The fake server of the third party, with the module's settings pointing at it | The same fake server, started for every deployable |
| LLM | `TestModel` or `FunctionModel`, injected through `FakeModels` | A fake Ollama server, set as `OLLAMA_BASE_URL`, streaming a committed answer |
| Firebase Auth | A fake token verifier, injected | The backend's debug user (`DEBUG=true`, `DEBUG_USER_JWT`), signed in through a Firebase session the test stores in the browser |
| Time | The injected clock | The real clock; time-driven behavior is tested in component tests |
| Events and tasks | Real, on Postgres | Real, on Postgres |
