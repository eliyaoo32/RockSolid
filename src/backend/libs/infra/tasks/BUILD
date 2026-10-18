python_sources(
    overrides={
        # tasks.py loads the migrations by path, so Pants cannot infer them.
        "tasks.py": {
            "dependencies": [
                "src/backend/libs/infra/tasks/migrations",
                "src/backend/libs/infra/tasks/migrations/versions",
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
