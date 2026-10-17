python_sources(
    overrides={
        # events.py loads the migrations by path, so Pants cannot infer them.
        "events.py": {
            "dependencies": [
                "src/backend/libs/infra/events/migrations",
                "src/backend/libs/infra/events/migrations/versions",
            ]
        },
    },
)

python_test_utils(
    name="test_utils",
)

python_tests(
    name="tests",
)
