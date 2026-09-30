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
  - `register_view` (alias `registerView`);
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

- **Stabilisation cycle** (phase C):
  - Entitlements implemented ([Entitlements](../security/entitlements.md)):
    - provider interface with a settings provider (off by default);
    - capacities enforced at every core creation point;
    - module entitlements ANDed with `EntityApp`;
    - `GET /api/resaas/entitlements/`;
    - `useEntitlementStore` in quasar_resaas.
  - HR residue removed: translation keys moved to the HR module, neutral examples in the docs.
  - `register_view` is canonical; `registerView` is a tested alias.
  - Dependencies:
    - django_resaas no longer depends on `dotenv==0.9.9`;
    - quasar_resaas dropped `vue3-apexcharts` and now declares `@codemirror/state` and
      `@codemirror/language`.
  - `pdfjs-dist` leaves the main bundle: `s-pdf-render-pro` is lazy.
  - Release safety: `make release-check` / `make publish` in both libraries validate before
    publishing, and push only after a successful publish.
  - Open issues found, not fixed in this cycle:
    - the deploy status/logs endpoints (see [Permissions](../security/permissions.md));
    - `BranchAPIView` has no per-action permission (any member of the Entity can create,
      change or delete its Branches);
    - `EntityAPIView.create` makes one "Main" Branch per admin;
    - firebase is always in the main bundle (making it lazy would change `initFirebase`).

## Next (plan, not implemented)

1. Public API policy (stable / advanced / internal / deprecated) and
   deprecation helpers.
2. CI for both libraries; publishing `quasar_resaas` to npm (the registry holds 0.0.4).
3. Quick Start / example app, then the public site.
