python_sources(
    overrides={
        # setup.py loads the migrations by path, so Pants cannot infer them.
        "setup.py": {
            "dependencies": [
                "src/backend/modules/users/migrations",
                "src/backend/modules/users/migrations/versions",
            ]
        },
    },
)
