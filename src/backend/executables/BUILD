# Import rules for every executable, written once. An executable uses modules through their
# services and the domain types they return, and never imports another executable; only its tests
# do, to run a feature that spans executables together.
__dependencies_rules__(
    (
        "/*/tests/framework/**",
        "./*",
        "../../*.py",
        # Other executables, for a feature that spans executables (`run_executables([...])`).
        "//src/backend/executables/*/*.py",
        "//src/backend/modules/*/services/**",
        "//src/backend/modules/*/domain/**",
        "//src/generated/**",
        "//src/backend/libs/**",
        # A third party's one fake, which E2E tests run too.
        "//src/tests/e2e/framework/fakes/**",
        "//3rdparty/python#*",
        "!*",
    ),
    (
        "/*/tests/**",
        "./**",
        "//src/backend/executables/*/*.py",
        "//src/backend/modules/*/services/**",
        "//src/backend/modules/*/domain/**",
        "//src/generated/**",
        "//src/backend/libs/**",
        "//src/tests/e2e/framework/fakes/**",
        "//3rdparty/python#*",
        "!*",
    ),
    (
        "*",
        "./*",
        "//src/backend/modules/*/services/**",
        "//src/backend/modules/*/domain/**",
        "//src/generated/**",
        "//src/backend/libs/**",
        "//3rdparty/python#*",
        "!*",
    ),
)
