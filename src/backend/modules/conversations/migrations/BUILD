python_sources()

python_tests(
    name="tests",
    dependencies=[
        # SQLAlchemy loads the driver named in the database URL at runtime.
        "3rdparty/python#asyncpg",
        # Alembic loads the migrations by path, so Pants cannot infer them.
        ":migrations",
        "./versions",
    ],
)
