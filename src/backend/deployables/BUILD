# Import rules for every deployable: it lists its executables and hands them to the runtime.
__dependencies_rules__(
    # The checks across deployables load every deployable and build its executables with the
    # test helpers.
    (
        "/tests/**",
        "./**",
        "//src/backend/deployables/**",
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

# Every deployable's entry point, owned here so the checks across deployables load them all.
python_sources(name="entry_points", sources=["*/main.py"])
