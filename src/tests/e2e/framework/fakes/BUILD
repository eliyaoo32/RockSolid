# The answer the fake Ollama streams to every agent.
files(name="testdata", sources=["testdata/*"])

python_sources(overrides={"ollama.py": {"dependencies": [":testdata"]}})

python_tests(name="tests")
