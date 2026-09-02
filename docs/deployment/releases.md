# Git Flow and Releases

A `develop` → `release/x.y.z` → `main` flow, tagged on merge. There's no release script in this
repo — this page documents the convention, checked by hand or in CI.

## Before starting a release

Always check whether one is already open, before doing anything else:

```bash
git branch -a | grep release
```

Starting a second release branch while one is still open is the single most common way this
process goes wrong — see [Troubleshooting](../troubleshooting/common-errors.md#release-already-exists).

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

Bump the version **after** confirming no release is already pending, never before. A version-bump
commit made before checking can end up on `develop` with no matching release branch to carry it —
the version then says one thing while the actual released code says another.

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
