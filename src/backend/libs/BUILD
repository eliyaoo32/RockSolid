# Import rules for every lib, written once. A lib never uses a module, with one exception: the
# runtime builds the users module's sign-in service, because every API needs the caller.
__dependencies_rules__(
    (
        "/infra/runtime/**",
        "./*",
        "//src/backend/libs/infra/cron/**",
        "//src/backend/libs/infra/events/**",
        "//src/backend/libs/infra/logs/**",
        "//src/backend/libs/infra/retry/**",
        "//src/backend/libs/testing/**",
        "//src/backend/modules/users/services/**",
        "//3rdparty/python#*",
        "!*",
    ),
    # Only tests may use the shared test helpers.
    (
        {"type": "python_test*", "path": "/infra/**"},
        "./*",
        "//src/backend/libs/infra/events/**",
        "//src/backend/libs/infra/logs/**",
        "//src/backend/libs/infra/retry/**",
        "//src/backend/libs/testing/**",
        "//3rdparty/python#*",
        "!*",
    ),
    # The events lib reuses the cron lib's wait and the retry strategies, and keeps its migrations
    # next to it.
    (
        "/infra/events/**",
        "./*",
        "./migrations",
        "./migrations/**",
        "//src/backend/libs/infra/cron/**",
        "//src/backend/libs/infra/logs/**",
        "//src/backend/libs/infra/retry/**",
        "//3rdparty/python#*",
        "!*",
    ),
    ("/infra/**", "./*", "//src/backend/libs/infra/logs/**", "//3rdparty/python#*", "!*"),
    # Test helpers run executables through the real runtime, with the users module's sign-in.
    (
        "/testing/**",
        "./*",
        "//src/backend/libs/infra/**",
        "//src/backend/modules/users/services/**",
        "//3rdparty/python#*",
        "!*",
    ),
)
