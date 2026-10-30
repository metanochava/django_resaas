# Git Flow and Releases

A `develop` → `release/x.y.z` → `main` flow, tagged on merge, driven by the `Makefile`.

## Commands

```bash
make releases        # develop -> bump version (patch/minor/major) -> release/x.y.z
make releasef        # release-check, then git flow release finish (local: nothing pushed)
make publish         # release-check, then upload to PyPI (push main, develop and the tag by hand)
```

`make release-check` runs on its own too. It fails, and nothing continues, when:

1. the working tree is not clean;
2. the tests fail (`pytest -x`);
3. the package does not build, or `twine check` rejects it;
4. the built wheel does not install in a fresh virtualenv (`pip check`), lacks the framework
   migrations, or ships tests.

**Failure behaviour.** `releasef` validates before `git flow release finish`, so a failing test
leaves the release branch open and untagged. `publish` uploads before pushing: if the upload
fails, nothing has been pushed. Fix the problem and run `make publish` again. The tag stays
local until the upload succeeds. `make upload` also runs `release-check` first.

## Continuous integration (GitHub Actions)

| Workflow | Runs on | Does |
|---|---|---|
| `.github/workflows/ci.yml` | push to `develop`, `main`, `release/**`, `hotfix/**`; pull requests | `pip install -e ".[dev,scaffold]"`, `pip check`, `manage.py check`, `makemigrations --check`, the full suite on Python 3.10 and 3.12; builds the package, `twine check --strict`, refuses a wheel with tests, installs it in a clean virtualenv |
| `.github/workflows/publish_pypi.yml` | a pushed tag | calls `ci.yml` first; only when it passes, checks that the tag equals the `pyproject.toml` version, builds and publishes with PyPI trusted publishing (`id-token: write`, no stored token). A version `make publish` already uploaded is skipped, not an error |

Validation and publication are separate jobs: a failing suite never reaches the upload. The
workflows hold no secret; trusted publishing must be configured on the PyPI project for this
repository.

## Before starting a release

Always check whether one is already open, before doing anything else:

```bash
git branch -a | grep release
```

> [!WARNING]
> Starting a second release branch while one is still open is the single most common way this
> process goes wrong — see
> [Troubleshooting](../troubleshooting/common-errors.md#fatal-there-is-an-existing-release-branch).

## Flow

```text
develop
   |
   v
release/x.y.z
   |
   +--> main       (merge - this is what ships)
   |
   +--> develop    (merge back - keeps develop caught up with the release's own fixes)
   |
   +--> tag        (vx.y.z, on main, after the merge)
```

## Version

The package version lives in `pyproject.toml`:

```bash
grep version pyproject.toml
# version = "0.0.461"
```

## Important rule

> [!WARNING]
> Bump the version **after** confirming no release is already pending, never before. A
> version-bump commit made before checking can end up on `develop` with no matching release
> branch to carry it — the version then says one thing while the actual released code says
> another.

## Diagnostics

```bash
git status
git branch -a
git tag --sort=-v:refname | head
grep version pyproject.toml
```

If a release branch exists that shouldn't (already merged, abandoned), resolve or delete it
explicitly rather than starting a new one alongside it — a leftover release branch will keep
tripping the "already exists" check for whoever runs it next.

## Supported versions

| Component | Supported |
|---|---|
| Python | 3.10 - 3.14 (`requires-python = ">=3.10"`, set by the pinned Django 5.2) |
| Django / DRF | `Django==5.2.10`, `djangorestframework==3.16.1` (pinned in `pyproject.toml`) |
| Optional extras | `scaffold` (black), `server` (gunicorn), `dev` (pytest, pytest-django, factory_boy). `celery` is a required dependency; the old `notifications` extra still resolves |

Installations install the framework from GitHub at a ref (the reference application's
`deploy.sh`: `pip install git+https://github.com/metanochava/django_resaas.git@<ref>`) or from
PyPI (`pip install django_resaas==x.y.z`); both build from the same `pyproject.toml`.

## Recovering from a defective release

PyPI never accepts the same version twice, so a broken release is fixed **forward**:

1. **Yank** the broken version on PyPI (project page → *Manage* → *Options* → *Yank*). pip stops
   choosing it for unpinned or range requirements; an installation pinned to it still gets it.
2. Fix on `develop` (or `make hotfixs` from `main`), then release the next patch version with the
   normal flow (`make releasef` / `make publish`).
3. Installations pinned to the broken version (or to a GitHub ref/tag of it) move to the fixed
   version explicitly; if the release shipped a migration, check
   [Upgrading](upgrading.md) before going back to an older version - never roll a database back by
   reinstalling an older package over migrations that already ran.

> [!NOTE]
> `make publish` currently runs `release-check` and uploads to PyPI; it does **not** push `main`,
> `develop` or the tag (despite the Makefile comment). Push them by hand after a successful upload.
