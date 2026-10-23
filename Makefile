# `make verify` is the single verification command: a change is done only when it passes.

.PHONY: verify verify-examples contracts generated generate web e2e e2e-frontend dev dev-backend dev-frontend

verify: contracts generated web e2e-frontend
	pants verify ::

# Runs the verification command with the rocksolid skill's examples in src/, on a copy of the working
# tree (its committed, changed, and new files) that is deleted afterwards. Only RockSolid runs it.
# The examples only add files; the one other change lists their contract module for Ruff.
EXAMPLES = .agents/skills/rocksolid/examples

verify-examples:
	@tmp=$$(mktemp -d); trap 'rm -rf "$$tmp" "$$tmp.index"' EXIT; \
	GIT_INDEX_FILE="$$tmp.index" git add --all && \
	git archive "$$(GIT_INDEX_FILE="$$tmp.index" git write-tree)" | tar -x -C "$$tmp" && \
	for file in $$(cd $(EXAMPLES) && find src -type f); do \
		if [ -e "$$tmp/$$file" ]; then echo "The example $$file would replace a file."; exit 1; fi; \
	done && \
	cp -R $(EXAMPLES)/src/. "$$tmp/src/" && \
	sed -i.bak 's/known-first-party = \[/known-first-party = ["clients", /' "$$tmp/pyproject.toml" && \
	$(MAKE) -C "$$tmp" generate verify

# Runs only the E2E tests.
e2e: e2e-frontend
	pants test src/tests/e2e::

# Builds the production frontend where the E2E tests serve it from, with a made-up Firebase web
# config that matches theirs (`src/tests/e2e/framework/system.py`).
e2e-frontend:
	FIREBASE_API_KEY=e2e-api-key FIREBASE_AUTH_DOMAIN=app.test FIREBASE_PROJECT_ID=rocksolid-e2e \
	FIREBASE_APP_ID=e2e-app \
	pnpm --filter @rocksolid/web-app exec vite build --outDir ../../tests/e2e/frontend-build --emptyOutDir

# Lints, typechecks, tests, and builds the TypeScript packages: the wireframe and the frontend.
web:
	pnpm install --frozen-lockfile
	pnpm -r run lint
	pnpm -r run typecheck
	pnpm -r run test
	pnpm -r run build

# Lints and formats the contracts.
contracts:
	buf lint
	buf format --diff --exit-code

# Fails when the committed generated code differs from what the contracts generate.
generated:
	@tmp=$$(mktemp -d); \
	buf generate -o $$tmp && diff -r -x BUILD -x __pycache__ -x package.json -x node_modules $$tmp/src/generated src/generated; \
	status=$$?; rm -rf $$tmp; \
	if [ $$status -ne 0 ]; then echo "Generated code is stale. Run: make generate"; fi; \
	exit $$status

generate:
	buf generate

# Runs the system locally on .env.development: Postgres in Docker, the backend, which restarts when
# its code changes, and the frontend's dev server. Ctrl+C stops both servers; Postgres keeps running.
DEV_ENV = set -a && . ./.env.development && set +a

dev:
	docker compose up --detach --wait
	pnpm install --frozen-lockfile
	$(DEV_ENV) && pants run src/backend/deployables/app/main.py -- migrate
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	$(DEV_ENV) && pants --loop run src/backend/deployables/app/main.py -- serve

dev-frontend:
	pnpm --filter @rocksolid/web-app dev
