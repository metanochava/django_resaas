# Git Flow and Releases

## Before starting

Check whether a release is already open:

``` bash
git branch -a | grep release
```

## Flow

``` text
develop
   |
   v
release/x.y.z
   |
   +--> main
   |
   +--> develop
   |
   +--> tag
```

## Important rule

The version bump must not happen before checking whether a release is
already pending. Otherwise, version-bump commits can end up without a
matching release branch.

## Diagnostics

``` bash
git status
git branch -a
git tag --sort=-v:refname | head
grep version pyproject.toml
```
