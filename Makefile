# `make verify` is the single verification command: a change is done only when it passes.

.PHONY: verify verify-examples framework-files contracts generated generate web e2e e2e-frontend dev dev-backend dev-frontend

verify: framework-files contracts generated web e2e-frontend
	pants verify ::

# RockSolid's files. A project never changes them: `make verify` fails when one differs from RockSolid
# at the branch in the project's `framework-ref` file (`main` without the file). RockSolid skips it.
# Whole paths: the project adds nothing inside them either.
FRAMEWORK_FILES = AGENTS.md CLAUDE.md Makefile buf.yaml buf.lock buf.gen.yaml pnpm-workspace.yaml \
	.github/workflows docs/guides docs/features/FEATURE_TEMPLATE.md \
	src/backend/libs src/backend/modules/BUILD src/backend/modules/users src/backend/modules/conversations \
	src/backend/executables/BUILD src/backend/executables/users_api src/backend/executables/conversations_api \
	src/backend/deployables/BUILD src/backend/deployables/tests \
	src/protos/users src/protos/conversations \
	src/clients/web-app/vite.config.ts src/clients/web-app/tsconfig.json src/clients/web-app/tsconfig.app.json \
	src/clients/web-app/tsconfig.node.json src/clients/web-app/eslint.config.js src/clients/web-app/eslint-rules \
	src/clients/web-app/.prettierrc src/clients/web-app/src/main.tsx src/clients/web-app/src/config.ts \
	src/clients/web-app/src/auth \
	src/clients/wireframe/vite.config.ts src/clients/wireframe/tsconfig.json src/clients/wireframe/tsconfig.app.json \
	src/clients/wireframe/tsconfig.node.json src/clients/wireframe/eslint.config.js src/clients/wireframe/eslint-rules \
	src/clients/wireframe/.prettierrc src/clients/wireframe/src/main.tsx \
	src/tests/e2e/sign_in_test.py src/tests/e2e/debug_user_test.py src/tests/e2e/display_name_test.py \
	src/tests/e2e/conversations_test.py
# Folders that hold RockSolid's files and the project's own files beside them: RockSolid's files stay
# as they are, and the project adds its own, such as its skills, generated code, and test drivers.
FRAMEWORK_FOLDERS = .agents .claude .pi src/generated src/clients/web-app/src/api \
	src/clients/web-app/tests/framework src/tests/e2e/framework \
	':(exclude)src/clients/web-app/tests/framework/fake-services.ts'
FRAMEWORK_REPOSITORY = https://github.com/eliyaoo32/RockSolid.git

framework-files:
	@if ! git rev-parse --git-dir > /dev/null 2>&1 || git remote get-url origin 2>/dev/null | grep -q 'eliyaoo32/RockSolid'; then exit 0; fi; \
	ref=$$(cat framework-ref 2>/dev/null || echo main); \
	git fetch --quiet --depth=1 $(FRAMEWORK_REPOSITORY) "$$ref" || exit 1; \
	changed=$$( { git diff --name-only FETCH_HEAD -- $(FRAMEWORK_FILES); \
		git diff --name-only --diff-filter=MD FETCH_HEAD -- $(FRAMEWORK_FOLDERS); } | sort -u ); \
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
