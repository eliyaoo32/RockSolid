# Import rules for every lib, written once. A lib never uses a module, with one exception: the
# runtime builds the users module's sign-in service, because every API and agent needs the
# caller, and keeps each agent's conversations in the conversations module.
__dependencies_rules__(
    # Tests come first, so their rule applies to them in every lib. Only tests may use the shared
    # test helpers.
    (
        {"type": "python_test*", "path": "/infra/**"},
        "./*",
        "//src/backend/libs/infra/agents/**",
        "//src/backend/libs/infra/cron/**",
        "//src/backend/libs/infra/events/**",
        "//src/backend/libs/infra/llm/**",
        "//src/backend/libs/infra/logs/**",
        "//src/backend/libs/infra/retry/**",
        "//src/backend/libs/infra/tasks/**",
        "//src/backend/libs/testing/**",
        "//src/backend/modules/conversations/domain/**",
        "//src/backend/modules/conversations/services/**",
        "//src/backend/modules/users/services/**",
        "//3rdparty/python#*",
        "!*",
    ),
    (
        "/infra/runtime/**",
        "./*",
        "//src/backend/libs/infra/agents/**",
        "//src/backend/libs/infra/cron/**",
        "//src/backend/libs/infra/events/**",
        "//src/backend/libs/infra/llm/**",
        "//src/backend/libs/infra/logs/**",
        "//src/backend/libs/infra/retry/**",
        "//src/backend/libs/infra/tasks/**",
        "//src/backend/libs/testing/**",
        "//src/backend/modules/conversations/domain/**",
        "//src/backend/modules/conversations/services/**",
        "//src/backend/modules/users/services/**",
        "//3rdparty/python#*",
        "!*",
    ),
    # The event bus and the task queue reuse the cron lib's wait, the database helpers, and the
    # retry strategies, and keep their migrations next to them.
    (
        ("/infra/events/**", "/infra/tasks/**"),
        "./*",
        "./migrations",
        "./migrations/**",
        "//src/backend/libs/infra/cron/**",
        "//src/backend/libs/infra/db/**",
        "//src/backend/libs/infra/logs/**",
        "//src/backend/libs/infra/retry/**",
        "//3rdparty/python#*",
        "!*",
    ),
    # The agents lib names its caller with the users module's user ID.
    (
        "/infra/agents/**",
        "./*",
        "//src/backend/modules/users/domain/**",
        "//3rdparty/python#*",
        "!*",
    ),
    # The database helpers sleep with the cron lib's wait.
    ("/infra/db/**", "./*", "//src/backend/libs/infra/cron/**", "//3rdparty/python#*", "!*"),
    ("/infra/**", "./*", "//src/backend/libs/infra/logs/**", "//3rdparty/python#*", "!*"),
    # Test helpers run executables through the real runtime, with the users module's sign-in.
    (
        "/testing/**",
        "./*",
        "//src/backend/libs/infra/**",
        "//src/backend/modules/users/domain/**",
        "//src/backend/modules/users/services/**",
        "//3rdparty/python#*",
        "!*",
    ),
)
