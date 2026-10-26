# `make verify` is the single verification command: a change is done only when it passes.

.PHONY: verify verify-examples framework-files contracts generated generate web e2e e2e-frontend dev dev-backend dev-frontend

verify: framework-files contracts generated web e2e-frontend
	pants verify ::

# RockSolid's files a project may change: the Shared and Project files in
# docs/guides/STARTING_AND_UPDATING_A_PROJECT.md. Every other file RockSolid has is RockSolid's: `make verify`
# fails in a project when one differs from RockSolid at the branch in the project's `framework-ref` file
# (`main` without the file). RockSolid skips it.
PROJECT_FILES = .env.development .gitignore README.md package.json pnpm-lock.yaml pants.toml pyproject.toml \
	skills-lock.json 3rdparty/python/requirements.txt 3rdparty/python/default.lock src/backend/deployables/app \
	src/clients/web-app/.gitignore src/clients/web-app/.prettierignore src/clients/web-app/index.html \
	src/clients/web-app/package.json src/clients/web-app/components.json src/clients/web-app/src/App.tsx \
	src/clients/web-app/src/App.test.tsx src/clients/web-app/src/components src/clients/web-app/src/views \
	src/clients/web-app/src/i18n src/clients/web-app/src/index.css src/clients/web-app/src/lib \
	src/clients/web-app/tests/sign-in.test.tsx src/clients/web-app/tests/framework/fake-services.ts \
	src/clients/wireframe/.gitignore src/clients/wireframe/.prettierignore src/clients/wireframe/README.md \
	src/clients/wireframe/index.html src/clients/wireframe/package.json src/clients/wireframe/components.json \
	src/clients/wireframe/src/App.tsx src/clients/wireframe/src/components src/clients/wireframe/src/i18n \
	src/clients/wireframe/src/index.css src/clients/wireframe/src/lib \
	src/tests/e2e/BUILD src/tests/e2e/conftest.py
# RockSolid's folders a project adds no file to.
FRAMEWORK_FOLDERS = .github/workflows docs/guides src/backend/libs \
	src/backend/modules/users src/backend/modules/conversations \
	src/backend/executables/users_api src/backend/executables/conversations_api src/backend/deployables/tests \
	src/protos/users src/protos/conversations src/clients/web-app/src/auth
FRAMEWORK_REPOSITORY = https://github.com/eliyaoo32/RockSolid.git

framework-files:
	@if ! git rev-parse --git-dir > /dev/null 2>&1 || git remote get-url origin 2>/dev/null | grep -q 'eliyaoo32/RockSolid'; then exit 0; fi; \
	ref=$$(cat framework-ref 2>/dev/null || echo main); \
	git fetch --quiet --depth=1 $(FRAMEWORK_REPOSITORY) "$$ref" || exit 1; \
	changed=$$( { git diff --name-only --diff-filter=MD FETCH_HEAD -- . $(foreach f,$(PROJECT_FILES),':(exclude)$(f)'); \
		git diff --name-only --diff-filter=A FETCH_HEAD -- $(FRAMEWORK_FOLDERS); } | sort -u ); \
	if [ -n "$$changed" ]; then \
		echo "This project changed RockSolid's files, which change only in RockSolid:"; \
		echo "$$changed" | sed 's/^/  /'; \
		echo "Undo these changes here. To change them, follow \"Change the Framework From a Project\" in"; \
		echo "docs/guides/STARTING_AND_UPDATING_A_PROJECT.md: open a RockSolid pull request, and use it here before it merges."; \
		echo "(Compared with RockSolid's $$ref, the branch in framework-ref, or main without that file.)"; \
		exit 1; \
	fi

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
