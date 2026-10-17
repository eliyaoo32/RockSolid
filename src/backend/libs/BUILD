# Import rules for every lib, written once. A lib never uses a module, with one exception: the
# runtime builds the users module's sign-in service, because every API needs the caller.
__dependencies_rules__(
    (
        "/infra/runtime/**",
        "./*",
        "//src/backend/libs/infra/cron/**",
        "//src/backend/libs/infra/logs/**",
        "//src/backend/libs/testing/**",
        "//src/backend/modules/users/services/**",
        "//3rdparty/python#*",
        "!*",
    ),
    # Only tests may use the shared test helpers.
    (
        {"type": "python_test*", "path": "/infra/**"},
        "./*",
        "//src/backend/libs/infra/logs/**",
        "//src/backend/libs/testing/**",
        "//3rdparty/python#*",
        "!*",
    ),
    ("/infra/**", "./*", "//src/backend/libs/infra/logs/**", "//3rdparty/python#*", "!*"),
    ("/testing/**", "./*", "//3rdparty/python#*", "!*"),
)
