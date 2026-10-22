python_sources(
    # SQLAlchemy loads the driver named in the database URL at runtime.
    dependencies=["3rdparty/python#asyncpg"],
)

python_test_utils(name="test_utils")

# The debug chat page tests serve in place of the CDN's, and a conversation an earlier release
# stored.
files(name="testdata", sources=["testdata/*"])

python_tests(name="tests", dependencies=[":testdata"])
