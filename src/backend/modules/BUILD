# Import rules for every module, written once. `/*/` is any module's folder, `./` is the folder of
# the file being checked, and `../` is its module's folder. The first matching selector applies.
__dependencies_rules__(
    # The conversations domain also holds Pydantic AI's messages, by the owner's decision.
    (
        "/conversations/domain/**",
        "//src/backend/modules/*/domain/**",
        "//3rdparty/python#pydantic",
        "//3rdparty/python#pydantic-ai-slim",
        "//3rdparty/python#pytest",
        "!*",
    ),
    # Domain code: domains and Pydantic only, so no database, provider, or transport code.
    (
        "/*/domain/**",
        "//src/backend/modules/*/domain/**",
        "//3rdparty/python#pydantic",
        "//3rdparty/python#pytest",
        "!*",
    ),
    # Repository interfaces: domains, and the transaction a save runs in.
    (
        "/*/repositories/*_repository.py",
        "//src/backend/modules/*/domain/**",
        "//src/backend/libs/infra/db/transaction.py",
        "!*",
    ),
    # Repository implementations and their tests: their own folder, domains, the transaction,
    # filtering, third parties.
    (
        "/*/repositories/**",
        "./*",
        "//src/backend/modules/*/domain/**",
        "//src/backend/libs/infra/db/transaction.py",
        "//src/backend/libs/infra/filtering/**",
        "//3rdparty/python#*",
        "!*",
    ),
    # Setup is the only service that builds implementations and runs migrations.
    (
        "/*/services/setup.py",
        "./*",
        "../repositories/**",
        "../migrations",
        "../migrations/**",
        "//src/backend/modules/*/domain/**",
        "//3rdparty/python#*",
        "!*",
    ),
    # Application services: their module's repository interfaces, never implementations, and the
    # events and tasks they write in a save's transaction.
    (
        "/*/services/**",
        "./*",
        "../repositories/*_repository.py",
        "//src/backend/modules/*/domain/**",
        "//src/backend/libs/infra/db/transaction.py",
        "//src/backend/libs/infra/events/**",
        "//src/backend/libs/infra/tasks/**",
        "//3rdparty/python#*",
        "!*",
    ),
    ("/*/migrations/**", "./**", "//3rdparty/python#*", "!*"),
    ("*", "!*"),
)
