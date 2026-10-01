# Git Flow and Releases

A `develop` → `release/x.y.z` → `main` flow, tagged on merge, driven by the `Makefile`.

## Commands

```bash
make releases        # develop -> bump version (patch/minor/major) -> release/x.y.z
make releasef        # release-check, then git flow release finish (local: nothing pushed)
make publish         # release-check, upload to PyPI, THEN push main, develop and the tag
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
