python_sources(
    overrides={
        # setup.py loads the migrations by path, so Pants cannot infer them.
        "setup.py": {
            "dependencies": [
                "src/modules/clients/migrations",
                "src/modules/clients/migrations/versions",
            ]
        },
    },
)
