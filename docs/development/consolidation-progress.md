# Consolidation & production readiness — progress

Tracks the multi-phase consolidation of RESAAS (modularity, packaging,
entitlements, public API, developer experience). Only the **Done** section
describes implemented behaviour. Everything under **Next** is a plan.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Where HR goes | Out of `django_resaas`, into the application that uses it, as its own `hr` module, keeping the Django app label `hr` | HR is domain, not framework. Keeping the label `hr` means tables, ContentTypes, permissions and `'hr.Employee'` references stay identical, so there is no data migration. There is no compatibility import, because the framework cannot depend on an application. |
| Framework migrations | Shipped with the package (done, see below) | Prerequisite to move any app safely. Per-environment generated migrations diverged between environments. |
| Pace | Phase by phase, reviewed before the next | The scope is large; each phase ships code + tests + docs |

## Audit (phase 1) — key findings

- The core (`saas`, `notifications`) does not import `hr`. It only names HR
  permission codenames in the admin profiles. The core already starts
  without HR.
- Applications depend on HR: `Employee` as the base of domain professionals,
  plus `Specialty` and `EmployeeSpecialty`.
- Migrations were not versioned: the framework's were generated inside the
  installed package, and differed per environment.
- No entitlement/licensing mechanism exists yet. `EntityType.license` is a
  placeholder text field.
- npm registry: `quasar_resaas` 0.0.4 vs 0.0.14xx in the repository. PyPI is
  current.
- Existing extension points to reuse:
  - `registerView`;
  - `<app>/dashboard.py` (autodiscovered);
  - `profiles.py` + `group_creator`;
  - `<app>/lang/`;
  - `sidebar.py`;
  - `App` / `EntityApp` (module activation);
  - `resaas_doctor` checks.

## Done

- **Shipped migrations** (phase A): one `0001_initial` per framework app,
  schema-identical to the existing environments (verified on copies of two
  real databases with different histories).
  - `resaas_migrations_rebaseline` aligns existing environments;
  - `test_shipped_migrations.py` guards models against missing migrations;
  - see [Upgrading](../deployment/upgrading.md).

## Next (plan, not implemented)

1. HR out of the core package into its own module (label `hr` kept),
   `django_resaas.hr` as a deprecated compatibility path.
2. Entitlements: a central service (features, capacities, modules) behind a
   provider interface. It is separate from authorization and enforced server-side.
3. Public API policy (stable / advanced / internal / deprecated) and
   deprecation helpers.
4. Packaging validation (clean `pip install`, `npm pack --dry-run`), release
   safety in the Makefiles, CI for `quasar_resaas`.
5. Quick Start / example app, then the public site.
