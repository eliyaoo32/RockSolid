python_sources(
    overrides={
        # setup.py loads the migrations by path, so Pants cannot infer them.
        "setup.py": {
            "dependencies": [
                "src/backend/modules/conversations/migrations",
                "src/backend/modules/conversations/migrations/versions",
            ]
        },
    },
)
