# `make verify` is the single verification command: a change is done only when it passes.
# BASE is the git ref that contracts must stay compatible with.
BASE ?= main

.PHONY: verify contracts generated generate web

verify: contracts generated web
	pants verify ::

# Lints, typechecks, tests, and builds the TypeScript packages: the wireframe and the frontend.
web:
	pnpm install --frozen-lockfile
	pnpm -r run lint
	pnpm -r run typecheck
	pnpm -r run test
	pnpm -r run build

# Lints and formats the contracts, and fails on changes that break existing clients.
contracts:
	buf lint
	buf format --diff --exit-code
	@if git cat-file -e $(BASE):buf.yaml 2>/dev/null; then \
		buf breaking --against '.git#ref=$(BASE)'; \
	else \
		echo "buf breaking: $(BASE) has no contracts yet, nothing to compare."; \
	fi

# Fails when the committed generated code differs from what the contracts generate.
generated:
	@tmp=$$(mktemp -d); \
	buf generate -o $$tmp && diff -r -x BUILD -x __pycache__ -x package.json -x node_modules $$tmp/src/generated src/generated; \
	status=$$?; rm -rf $$tmp; \
	if [ $$status -ne 0 ]; then echo "Generated code is stale. Run: make generate"; fi; \
	exit $$status

generate:
	buf generate
