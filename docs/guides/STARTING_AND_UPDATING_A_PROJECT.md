# Starting and Updating a Project

A project is a clone of RockSolid that keeps RockSolid's git history. RockSolid holds only the framework: guidelines, skills, tooling, and shared libraries, with no product code. Its example feature lives in the `rocksolid` skill (`.agents/skills/rocksolid/examples/`), so a project starts with no example code in `src/`. Every change to RockSolid reaches every project through `git merge`.

## Rules

- **The Framework Changes Only in RockSolid:** A change to a framework file is made in RockSolid, through a RockSolid pull request, and reaches the project through the next update. A project never changes a framework file itself.
- **Projects Merge, Never Rebase or Cherry-Pick:** An update merges `framework/main` whole. A cherry-picked framework commit comes back again in the next merge and conflicts with itself.
- **Rules for One Project Are Skills:** `AGENTS.md` belongs to the framework. A rule that holds only in one project goes in a skill in that project's `.agents/skills/<project>-<topic>/`, which no framework update touches.
- **Update Often:** Each update is a small merge with few conflicts.

## Who Owns Which Files

| Owner | Files | Edited by |
|---|---|---|
| Framework | `AGENTS.md` (and `CLAUDE.md`, its link), `.agents/`, `.claude/`, `.pi/`, `README.md`, `docs/guides/`, `docs/features/FEATURE_TEMPLATE.md`, `Makefile`, `buf.yaml`, `buf.gen.yaml`, `.github/workflows/`, `pnpm-workspace.yaml`, `src/backend/libs/`, `src/backend/modules/users/`, `src/backend/modules/conversations/`, `src/backend/deployables/BUILD`, `src/backend/deployables/tests/`, `src/backend/executables/users_api/`, `src/protos/users/`; in `src/clients/web-app/` and `src/clients/wireframe/`: `vite.config.ts`, `tsconfig*.json`, `eslint.config.js`, `eslint-rules/`, `.prettierrc`, `components.json`, `main.tsx`; and `src/clients/web-app/src/{auth,api}/`, `src/clients/web-app/src/config.ts`, `src/clients/web-app/tests/framework/`, `src/tests/e2e/framework/` (except `agents.py`, which a project with an agent copies from the `rocksolid` skill's examples), `src/tests/e2e/sign_in_test.py` | RockSolid only |
| Shared | `3rdparty/python/requirements.txt`, `3rdparty/python/default.lock`, `pants.toml`, `pyproject.toml`, `.gitignore`, every `package.json`, `pnpm-lock.yaml`, `src/backend/deployables/app/main.py`, `src/clients/web-app/src/App.tsx`, `src/clients/wireframe/src/App.tsx`, both apps' `src/i18n/resources.ts`, `src/clients/wireframe/README.md` | Both. The update resolves their conflicts as described below. |
| Project | `docs/features/<NNN>_*.md`, `src/protos/<module>/`, `src/generated/`, `src/backend/modules/<module>/`, the other `src/backend/executables/`, the rest of `src/backend/deployables/` and of `src/clients/web-app/` and `src/clients/wireframe/`, the other tests in `src/tests/e2e/` | The project only |

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
   - `pants.toml`, `pyproject.toml`, and `.gitignore`: keep both sides' changes, such as both sides' packages in `known-first-party`.
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

## Change the Framework From a Project

A project that needs a fix or a feature in a framework file makes it in RockSolid, from a branch cut from `framework/main`, so the branch carries no project code.

1. Start the branch in its own worktree, next to the project's folder:
   ```bash
   git fetch framework
   ```
   ```bash
   git worktree add ../<project>-framework -b <branch> framework/main
   ```
2. In that folder, make the change test first, and run both verification commands:
   ```bash
   make verify
   ```
   ```bash
   make verify-examples
   ```
3. Push the branch to RockSolid and open a pull request there. Without write access to RockSolid, fork it, push to the fork, and open the pull request from it.
   ```bash
   git push framework <branch>
   ```
   ```bash
   gh pr create --repo eliyaoo32/RockSolid --base main --head <branch>
   ```
4. After the owner merges it, the project takes it with its next update. A project that cannot wait merges the branch itself (`git merge framework/<branch>`), never cherry-picks it. RockSolid squash-merges, so the next update brings the same change again: identical changes merge cleanly, and a file the review changed takes the framework's version.
5. Remove the worktree:
   ```bash
   git worktree remove ../<project>-framework
   ```
