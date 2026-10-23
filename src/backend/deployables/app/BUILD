# The Linux platforms of the python:3.14-slim base image, captured with
# `pex3 interpreter inspect --markers --tags` inside it.
file(name="linux_amd64", source="linux_amd64.json")
file(name="linux_arm64", source="linux_arm64.json")

pex_binary(
    name="bin",
    entry_point="main.py",
    complete_platforms=[":linux_amd64", ":linux_arm64"],
    # Alembic reads the migration files from disk, so the code must be unpacked into a venv.
    execution_mode="venv",
)

docker_image(
    name="image",
    repository="rocksolid/app",
    image_tags=["latest"],
)
