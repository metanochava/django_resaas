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

- **HR out of the framework (backend)** (phase B): `django_resaas.hr`
  removed, so the core names no business module:
  - core URLs no longer include it;
  - module permissions go through the public `ensure_module_permissions`;
  - the administration profiles only name core permissions;
  - default modules come from `settings.RESAAS_DEFAULT_MODULES`;
  - scaffold protection covers framework apps only.

  The core's tests use the dev demo's neutral test domain (`Category`,
  `Member`, `Rate`, `Visit`, `Agreement`) instead of HR models. Two
  framework mechanisms whose only tests lived in HR (field-level permissions,
  person registration) now have their own. Tenant fixtures are public:
  `django_resaas.testing`. See
  [Upgrading](../deployment/upgrading.md) and
  [Building a module](building-a-module.md).

- **HR out of the framework (frontend)**: `quasar_resaas` ships no HR. Its
  pages, 42 stores and routes moved to the application's frontend
  (`front/src/pages/hr`, `hrRoutes`). `useEmployeeStore` is no longer
  exported. `FormTwo`, `AutoCrud` and `PersonProfilePanel` are now named
  exports, so a module's pages import only from `'quasar_resaas'`. See
  quasar_resaas [Building a module](https://github.com/metanochava/quasar_resaas/blob/main/docs/quasar-resaas/development/building-a-module.md).

## Next (plan, not implemented)

1. Entitlements: a central service (features, capacities, modules) behind a
   provider interface. It is separate from authorization and enforced server-side.
2. Public API policy (stable / advanced / internal / deprecated) and
   deprecation helpers.
3. Packaging validation (clean `pip install`, `npm pack --dry-run`), release
   safety in the Makefiles, CI for `quasar_resaas`.
4. Quick Start / example app, then the public site.
