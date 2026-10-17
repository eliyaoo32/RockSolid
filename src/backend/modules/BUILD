# Import rules for every module, written once. `/*/` is any module's folder, `./` is the folder of
# the file being checked, and `../` is its module's folder. The first matching selector applies.
__dependencies_rules__(
    # Domain code: domains and Pydantic only, so no database, provider, or transport code.
    (
        "/*/domain/**",
        "//src/backend/modules/*/domain/**",
        "//3rdparty/python#pydantic",
        "//3rdparty/python#pytest",
        "!*",
    ),
    # Repository interfaces: domains only.
    ("/*/repositories/*_repository.py", "//src/backend/modules/*/domain/**", "!*"),
    # Repository implementations and their tests: their own folder, domains, filtering, third parties.
    (
        "/*/repositories/**",
        "./*",
        "//src/backend/modules/*/domain/**",
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
    # Application services: their module's repository interfaces, never implementations.
    (
        "/*/services/**",
        "./*",
        "../repositories/*_repository.py",
        "//src/backend/modules/*/domain/**",
        "//3rdparty/python#*",
        "!*",
    ),
    ("/*/migrations/**", "./**", "//3rdparty/python#*", "!*"),
    ("*", "!*"),
)
