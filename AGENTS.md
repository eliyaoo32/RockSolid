# Guidelines

## Testing

### Test Folders
```
modules/contacts/domain/contact.py
modules/contacts/domain/contact_test.py           # unit test, next to its source
executables/contacts_api/tests/contacts_test.py   # component tests, named after the feature
executables/contacts_api/tests/framework/         # this executable's drivers, fixtures, and fakes
libs/testing/                                     # fakes and helpers shared by several executables
e2e/tests/contact_management.spec.ts              # E2E tests
e2e/framework/                                    # E2E drivers, fixtures, and fakes
```
- Drivers, fixtures, and fakes live only in `framework/` folders or `libs/testing/`, never in test files or product code.
- Only test code may import `libs/testing/`.

### Test-Driven Development
Every production change follows Red-Green-Refactor:
1. **Red:** Write a test for the expected behavior first. Run it and see it fail with the expected assertion failure.
2. **Green:** Write the minimum code that makes it pass. Run the suite and see every test pass.
3. **Refactor:** Clean up the code and the tests, keeping every test green.

### Test Levels
- **Unit Tests:** Cover the domain code in `modules/*/domain/`: entities, value objects, and domain services. Every source file in `domain/` has a test file next to it (`contact.py` → `contact_test.py`). Domain code does no I/O, so unit tests need no fakes.
- **Component Tests:** Test one executable as a whole, through its contract: RPC calls for an RPC service, a published event for a domain-events listener, a queued task for a tasks consumer, a clock tick for a cron scheduler, and a conversation for an AI agent. Each test runs a complete flow the way a client uses the component: for an RPC service, create a contact, list it, update it, and get it again. Services, repositories, and the database (an ephemeral Postgres) are real parts of the component and are never tested on their own; everything outside the executable is a fake.
- **End-to-End (E2E) Tests:** Test the whole system: the real deployables and the production frontend build, driven through the UI in a real browser with Playwright. E2E tests simulate complicated, realistic user journeys: long flows across several screens and features, done the way real users do them, including mistakes, corrections, and returning later to continue. Third parties are fakes.
  - **API-Driven Before the UI Exists:** A feature whose UI does not exist yet runs its E2E tests through the ConnectRPC API, with the same rules. The feature that adds the UI adds the UI-driven tests.
  - **Several Scenarios per Feature:** Each feature has several E2E tests, each a chain of steps: the main lifecycle, and one for each family of failures, such as one of our services failing or a third party answering wrongly.
- **Agents in Tests:** Component and E2E tests run AI agents on Pydantic AI's `TestModel` or `FunctionModel`. Only evals call a real model, and they run outside the verification command.

### Coverage and Mutation Testing
- **100% Coverage:** Every line and branch is covered. The wireframe, generated code, and generated UI primitives are exempt.
- **Genuine Assertions:** Tests assert real outputs and state changes, and fail whenever the behavior breaks. A test without a meaningful assertion is a bug.
- **Mutation Testing on Domain Code:** For every change to `domain/`, run mutation testing on the changed files and kill every surviving mutant with a new assertion.

### Test Files
- **Feature-Named Files:** A test file is named after the feature it covers, never after a layer or an endpoint (`contact_import_test.py`, not `rpc_test.py`). Group a feature's scenarios into as few files as its size allows.

### Drivers
- **Driver Pattern:** Component and E2E tests read as scenarios. A driver hides how each step is done: `driver.when.*` performs actions, and `driver.get.*` reads results.
  ```python
  driver.when.create_contact(name="Avi", email="avi@example.com")
  driver.when.rename_contact(name="Avi Cohen")
  assert driver.get.contact().name == "Avi Cohen"
  ```

### Required Scenarios
- **Permissions:** Every operation that requires a permission has a component test proving that a caller without credentials gets `UNAUTHENTICATED`, a caller without the permission gets `PERMISSION_DENIED`, and no state changes.
- **Tenant Isolation:** Every tenant-owned resource has component tests with two tenants holding identical data, proving that:
  - each tenant's List returns only its own resources;
  - a Get, Update, or Delete on the other tenant's resource is rejected, changes nothing, and does not reveal that the resource exists;
  - the same value under two tenants, such as the same contact email, belongs to each tenant independently.
- **Agents Act as Their User:** Every agent has a component test proving it cannot do anything its signed-in user cannot do.

### Scenario Depth
Component and E2E tests model realistic, multi-step state changes:
- **State-Action Matrix:** For every entity with states, test each action both in the states that allow it and in the states that block it.
- **Chained Lifecycles:** Test chains of actions across state changes: an action succeeds, the state changes, the same action is blocked, the state is restored, and the action succeeds again.
- **Full Recovery:** Every error scenario also runs the recovery (fixing the cause, retrying, or re-enabling) and asserts the system works again.
- **Real Side Effects:** When an action changes another part of the system, assert that change directly, in the same step.
- **Input Preservation:** When an action is blocked, assert that the user's input and context are kept.
- **Crash Recovery:** For every row in a blueprint's Failures and Recovery section, a test stops the component at that point, starts it again, and asserts the final state: nothing lost, and nothing applied twice.

### Fakes and Test Infrastructure
Only the deployable creates infra and injects it, so tests swap every external dependency the same way: by injecting a fake.
- **Production Bootstrapper:** Tests boot an executable with the production bootstrapper and inject fakes in place of real infra, so the tests exercise the real wiring.
- **Never a Real Third Party:** No test sends a request to a real external service. A test that reaches one is a bug.
- **Injected Clock:** Code never reads the current time directly; it gets a clock through injection, and tests move it forward.
- **No Sleeping:** Tests never sleep to wait for asynchronous effects. They poll with `eventually(...)` until the effect appears or a timeout fails the test.

| Dependency | Component tests | E2E tests |
|---|---|---|
| Database | Real ephemeral Postgres (testcontainers); each test rolls back | Real ephemeral Postgres |
| Other RPC services | A fake implementation of the generated service, served in-process over the ASGI transport | The real deployable, or the same fake |
| Third-party HTTP APIs | Recorded responses replayed with `pytest-recording`; `respx` for one-off stubs | A fake server per third party, serving committed fixtures |
| LLM | `TestModel` or `FunctionModel`, injected | The test model, selected through an environment variable |
| Firebase Auth | A fake token verifier, injected | The Firebase Auth emulator |
| Time | The injected clock | The injected clock |
| Events and tasks | Real, on Postgres | Real, on Postgres |
