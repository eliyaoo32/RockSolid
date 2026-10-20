# The answer the fake Ollama streams to every agent.
files(name="testdata", sources=["testdata/*"])

python_sources(overrides={"fake_ollama.py": {"dependencies": [":testdata"]}})
