# Starting and Updating a Project

A project is a clone of RockSolid that keeps RockSolid's git history. RockSolid holds only the framework: guidelines, skills, tooling, and shared libraries, with no product code. Every change to RockSolid reaches every project through `git merge`.

## Rules

- **The Framework Changes Only in RockSolid:** A change to a framework file is made in RockSolid, through a RockSolid pull request, and reaches the project through the next update. A project never changes a framework file itself.
- **Projects Merge, Never Rebase or Cherry-Pick:** An update merges `framework/main` whole. A cherry-picked framework commit comes back again in the next merge and conflicts with itself.
- **Rules for One Project Are Skills:** `AGENTS.md` belongs to the framework. A rule that holds only in one project goes in a skill in that project's `.agents/skills/<project>-<topic>/`, which no framework update touches.
- **Update Often:** Each update is a small merge with few conflicts.

## Who Owns Which Files

| Owner | Files | Edited by |
|---|---|---|
| Framework | `AGENTS.md` (and `CLAUDE.md`, its link), `.agents/`, `.claude/`, `.pi/`, `README.md`, `docs/guides/`, `docs/features/FEATURE_TEMPLATE.md`, `Makefile`, `buf.yaml`, `buf.gen.yaml`, `.github/workflows/`, `pnpm-workspace.yaml`, `src/backend/libs/`, `src/backend/modules/users/`, `src/backend/executables/users_api/`, `src/protos/users/`; in `src/frontend/` and `src/wireframe/`: `vite.config.ts`, `tsconfig*.json`, `eslint.config.js`, `eslint-rules/`, `.prettierrc`, `components.json`, `main.tsx`; and `src/frontend/src/{auth,api}/`, `src/frontend/src/config.ts`, `src/frontend/tests/framework/` | RockSolid only |
| Shared | `3rdparty/python/requirements.txt`, `3rdparty/python/default.lock`, `pants.toml`, `.gitignore`, every `package.json`, `pnpm-lock.yaml`, `src/backend/deployables/backend/main.py`, `src/frontend/src/App.tsx`, `src/wireframe/src/App.tsx`, both apps' `src/i18n/resources.ts`, `src/wireframe/README.md` | Both. The update resolves their conflicts as described below. |
| Project | `docs/features/<NNN>_*.md`, `src/protos/<module>/`, `src/generated/`, `src/backend/modules/<module>/`, the other `src/backend/executables/`, the rest of `src/backend/deployables/` and of `src/frontend/` and `src/wireframe/`, `src/e2e/` | The project only |

## Start a Project

1. Create an empty repository on GitHub for the project, with no README, license, or `.gitignore`, so it has no commits of its own.
2. Clone RockSolid under the project's name:
   ```bash
   git clone https://github.com/eliyaoo32/RockSolid.git <project>
   ```
3. In the new folder, name the RockSolid remote `framework`, and add the project's repository as `origin`:
   ```bash
   git remote rename origin framework
   ```
   ```bash
   git remote add origin <project-repository-url>
   ```
4. Push the history to the project's repository:
   ```bash
   git push -u origin main
   ```

GitHub's "Use this template" starts a repository with no shared history, so later merges fail. A GitHub fork is not possible into the account that owns RockSolid. A clone works in both cases.

## Update a Project

1. Start a branch for the update:
   ```bash
   git switch -c framework-update
   ```
2. Fetch and merge the framework:
   ```bash
   git fetch framework
   ```
   ```bash
   git merge framework/main
   ```
3. Resolve the conflicts in the shared files:
   - `requirements.txt`: keep the lines from both sides.
   - `default.lock`: take the framework's version (`git checkout --theirs 3rdparty/python/default.lock`). The next step regenerates it.
   - `package.json`, `main.py`, `App.tsx`, and `resources.ts`: keep the dependencies, executables, routes, and keys from both sides.
   - `pnpm-lock.yaml`: take the framework's version (`git checkout --theirs pnpm-lock.yaml`). The next step regenerates it.
   - `pants.toml` and `.gitignore`: keep both sides' changes.
4. Regenerate everything generated, whether or not it conflicted, since the merged requirements and contracts can differ from both sides:
   ```bash
   pants generate-lockfiles
   ```
   ```bash
   pnpm install
   ```
   ```bash
   make generate
   ```
5. Run the verification command, and fix the project's code until it passes:
   ```bash
   make verify
   ```
6. Commit the merge, push the branch, and open a pull request. The description names the framework commit the project now matches (`git rev-parse --short framework/main`).
