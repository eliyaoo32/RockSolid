# Only test code uses the test helpers: test files, their conftest.py files and framework/
# folders, the helpers themselves, and the E2E tests.
__dependents_rules__(
    (
        "*",
        "//src/backend/**/*_test.py",
        "//src/backend/**/conftest.py",
        "//src/backend/**/tests/**",
        "//src/backend/libs/testing/**",
        "//src/tests/**",
        "!*",
    ),
)

python_sources(
    # SQLAlchemy loads the driver named in the database URL at runtime.
    dependencies=["3rdparty/python#asyncpg"],
)

python_test_utils(
    name="test_utils",
)

python_tests(
    name="tests",
)
