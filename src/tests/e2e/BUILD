# The production frontend, built for the E2E tests by `make e2e-frontend`.
files(name="frontend_build", sources=["frontend-build/**"])

python_test_utils(name="test_utils")

python_tests(
    dependencies=[
        ":frontend_build",
        # The tests run the backend deployable as its own process, from its entry point.
        "src/backend/deployables:entry_points",
        # Provides the browser fixtures; no test imports it.
        "3rdparty/python#pytest-playwright",
    ],
    timeout=300,
)
