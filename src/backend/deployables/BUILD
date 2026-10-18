# Import rules for every deployable: it lists its executables and hands them to the runtime.
__dependencies_rules__(
    # The checks across deployables build every deployable's executables with the test helpers.
    (
        "/deployables_test.py",
        "./**",
        "//src/backend/executables/*/*.py",
        "//src/backend/libs/**",
        "//3rdparty/python#*",
        "!*",
    ),
    (
        "*",
        "./**",
        "//src/backend/executables/*/*.py",
        "//src/backend/libs/infra/**",
        "//3rdparty/python#*",
        "!*",
    ),
)

# Every deployable's entry point, so the checks can tell when a deployable is missing from them.
files(name="entry_points", sources=["*/main.py"])

python_tests(name="tests", dependencies=[":entry_points"])
