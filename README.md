# 🚀 django_resaas

**The framework you've been missing for building multi-tenant SaaS apps in Django — without reinventing the wheel on every project.**

[![PyPI](https://img.shields.io/badge/pypi-django__resaas-3776AB?logo=pypi&logoColor=white)](https://pypi.org/project/django_resaas/)
[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Django](https://img.shields.io/badge/django-5.2-0C4B33?logo=django&logoColor=white)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-active%20development-orange)](https://github.com/metanochava/django_resaas)

---

If you've ever built a SaaS API in Django, you know the drill: multi-tenancy, per-group and per-branch permissions, soft delete, file uploads, PDF generation, i18n, plan-based billing… all of it **again**, project after project.

**django_resaas** solves that part once and for all. It's a framework built on top of Django + DRF that gives any application a production-ready foundation: multi-tenancy, RBAC, smart CRUD, dynamic search, per-client feature modules, and billing — so your team can focus on what actually matters: the business.

```bash
pip install django_resaas
```

---

## Table of contents

- [Why it exists](#-why-it-exists)
- [Features](#-features)
- [Installation & setup](#️-installation--setup)
- [Architecture](#-architecture)
- [Full example in 3 files](#-full-example-in-3-files)
- [Multi-tenancy & RBAC](#-multi-tenancy--rbac)
- [Soft delete](#-soft-delete)
- [Automatic search & filters](#-automatic-search--filters)
- [Per-client modules + billing](#-per-client-modules--billing)
- [Middlewares](#-middlewares)
- [Internationalization (i18n)](#-internationalization-i18n)
- [CLI / management commands](#-cli--management-commands)
- [Tech stack](#-tech-stack)
- [Documentation](#-documentation)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Why it exists

> "Building SaaS shouldn't be repetitive."

Every multi-tenant SaaS app ends up needing the same set of building blocks. `django_resaas` ships them ready-made, tested, and consistent with each other:

| Without django_resaas | With django_resaas |
|---|---|
| Multi-tenancy hand-rolled on every project | `BaseModel` already ships `entity` + `branch` |
| Permissions checked manually in every view | Automatic RBAC via `Entity` + `Branch` + `Group` |
| CRUD written from scratch for every resource | `BaseAPIView` gives full CRUD in ~5 lines |
| Destructive delete with no way back | Native soft delete + restore + hard delete |
| Custom search per endpoint | Automatic dynamic search (`?search=`) |
| "All or nothing" modules | Per-client module activation (`App` + `EntityApp`) |
| Translations scattered across the code | Central i18n system (DB + `lang/` files) |

---

## ✨ Features

* 🔐 **RBAC** — permissions by `User` + `Group` + context (`Entity`/`Branch`)
* 🏢 **Native multi-tenancy** — isolation by `Entity` and `Branch`
* ⚡ **Automatic CRUD** — `BaseAPIView` with pagination, ordering, filtering and permissions built in
* 🔎 **Dynamic search** — automatic search across text fields and relations
* ♻️ **Soft delete** — `delete()` / `restore()` / `hard_delete()` + dedicated managers
* 🧩 **Per-client modules** — toggle features on/off per entity without a deploy (`App` + `EntityApp`)
* 📎 **Files & PDF** — secure uploads, automatic metadata, PDF generation (WeasyPrint)
* 🔑 **JWT auth + 2FA** — `simplejwt`, OTP (`pyotp`) and QR codes built in
* 🌍 **Built-in i18n** — file-based translations (`pt-pt`, `en-us`, `es-es`, `fr-fr`) and database-backed
* 🌐 **Dedicated middlewares** — tenant context, frontend protection and file access control
* 💵 **Native money support** (`django-money`)

---

## ⚙️ Installation & setup

```bash
pip install django_resaas
# or, for local development:
pip install -e .
```

```python
# settings.py
INSTALLED_APPS = [
    ...
    "django_resaas",
    "hr",  # example module included
]

MIDDLEWARE = [
    ...
    "django_resaas.core.middleware.tenant.TenantContextMiddleware",
    "django_resaas.core.middleware.front_end.FrontEndMiddleware",
]
```

```bash
make migrate
make superuser
make run          # http://0.0.0.0:7002
```

---

## 🧠 Architecture

```text
User
 ↓
Person
 ↓
Employee (HR)
 ↓
Entity (tenant)
 ↓
Branch
 ↓
Groups + Permissions
```

**Key concepts:**

| Concept | Role |
|---|---|
| `Entity` | The tenant — typically the client/company |
| `Branch` | A unit/location within an `Entity` |
| `Person` | Human data (name, email, contacts) |
| `User` | Authentication |
| `BranchUserGroup` | Links `User` + `Branch` + `Group`, allowing multiple groups per branch |

---

## 🧪 Full example in 3 files

**Model**

```python
from django.db import models
from django_resaas.core.base.models import BaseModel

class Employee(BaseModel):
    person = models.ForeignKey("django_resaas.Person", on_delete=models.CASCADE)
    role = models.CharField(max_length=100)
```

`BaseModel` already ships `entity`, `branch`, `created_at`/`updated_at`, `created_by`/`updated_by` and soft delete.

**Serializer**

```python
from django_resaas.core.base.serializers import BaseSerializer

class EmployeeSerializer(BaseSerializer):
    class Meta:
        model = Employee
        fields = "__all__"
```

**View**

```python
from django_resaas.core.base.views import BaseAPIView, registerView

@registerView(module="hr")
class EmployeeView(BaseAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
```

That's enough to automatically get: full CRUD, multi-tenant isolation, permissions, search, soft delete, restore, and protection based on the active module.

---

## 🔐 Multi-tenancy & RBAC

Tenant context is never trusted from raw client-supplied values. It travels as a single **signed, short-lived token**, issued by the API after checking the user actually has access to the `Entity`/`Branch`/`Group` requested.

**1. Issue a context**, once the user is authenticated:

```http
POST /api/resaas/context/
Authorization: Bearer <access_token>

{
  "entity_id": "...",
  "branch_id": "...",   // optional
  "group_id": "..."     // optional
}
```

`ResaasContextService` validates access (via `EntityUser` / `BranchUser` / `BranchUserGroup`, with a superuser/entity-admin bypass) and signs the result with `django.core.signing` — versioned and bound to a TTL (1h by default, `RESAAS_CONTEXT_TTL` setting):

```json
{ "token": "<signed-context-token>", "context": { "entity_id": "...", "branch_id": "...", "group_id": "..." } }
```

**2. Send it back on every request**, alongside auth and language — three headers, one job each:

| Header | Purpose |
|---|---|
| `Authorization` | `Bearer <JWT>` — **who** you are |
| `X-RESAAS-Context` | signed tenant context — **where** you're operating (`entity`/`branch`/`group`) |
| `L` | active language id |

`TenantContextMiddleware` decodes the token and verifies its signature and expiry on every request, exposing:

```python
request.entity_type_id
request.entity_id
request.branch_id
request.group_id
```

`BaseAPIView` then re-validates that the context still belongs to the authenticated user (`ResaasContextService.validate_for_user`) before touching the queryset — a forged, expired, or replayed token from another user/tenant is rejected even if it was valid at issue time.

If a resource's module isn't active for the `Entity`, access is blocked automatically — no extra code in the view.

> ⚠️ **Breaking change from earlier versions:** the old scheme (raw `ET` / `E` / `S` / `G` headers sent directly by the client) has been replaced by the signed `X-RESAAS-Context` token above. If you're upgrading, swap those headers for a call to `POST /resaas/context/` and forward the returned token instead.

---

## 🔁 Soft delete

```python
obj.delete()        # soft delete
obj.restore()       # restore
obj.hard_delete()   # permanently delete
```

```python
Model.objects           # active only
Model.deleted_objects    # deleted only
Model.all_objects        # everything
```

---

## 🔎 Automatic search & filters

```http
GET /api/employees/?search=john
```

`BaseAPIView` automatically searches text fields and relations (`ForeignKey`), with no per-endpoint configuration required.

---

## 🧩 Per-client modules

Each `Entity` only sees the modules it has activated:

| Entity | Module | Status |
|---|---|---|
| Company A | HR | ✅ |
| Company A | CRM | ❌ |

Activation is a direct `App` ↔ `Entity` link via `EntityApp` (toggled with its `state` field):

```python
EntityApp.objects.get_or_create(app=app, entity=entity, state=1)
```

> There is no plan-based billing layer yet (no `Plan`/`EntityPlan` model, no automatic
> plan-to-module sync) - that's tracked under [Roadmap](#-roadmap). Module activation today is a
> direct per-entity toggle, as used by `python manage.py create_root` (see
> [`docs/development/management-commands.md`](docs/development/management-commands.md)).

---

## 🌐 Middlewares

| Middleware | Responsibility |
|---|---|
| `TenantContextMiddleware` | Decodes the signed `X-RESAAS-Context` token and resolves `entity`, `branch`, `group` (`L` header for language) |
| `FrontEndMiddleware` | Protects access via `FEK`/`FEP` frontend credentials and route/HTTP-method permissions |
| `FileAccessMiddleware` | Controls access to protected files and media |

---

## 🌍 Internationalization (i18n)

Translations are resolved in cascade — database first, then each app's `lang/` files — with automatic caching:

```python
from django_resaas.core.utils.translate import Translate

Translate.tdc(request, "Register")
```

Languages included out of the box: `pt-pt`, `en-us`, `es-es`, `fr-fr`.

---

## 🛠 CLI / management commands

```bash
python manage.py setup             # initial SaaS bootstrap
python manage.py create_entity     # creates a new Entity (tenant)
python manage.py create_root       # creates the root user
python manage.py sync_language     # loads the default languages
python manage.py sync_actions      # syncs views registered in VIEW_REGISTRY
python manage.py check              # Django's system check framework
python manage.py check_metano       # validates compliance with the MetanoStack standard
```

---

## 🧰 Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2 + Django REST Framework |
| Auth | `djangorestframework-simplejwt`, 2FA (`pyotp`, `qrcode`) |
| Database | PostgreSQL (`psycopg`) |
| Documents | WeasyPrint (PDF), `python-barcode` |
| Filtering | `django-filter` |
| Money | `django-money` |
| Deployment | Gunicorn |

---

## 📚 Documentation

Full technical documentation lives in [`docs/`](docs/README.md):

- [Architecture](docs/architecture/overview.md) · [Multi-tenancy](docs/architecture/multi-tenancy.md) · [Request lifecycle](docs/architecture/request-lifecycle.md) · [Middleware](docs/architecture/middleware.md)
- [Schema 1.0 contract](docs/api/schema-contract.md) · [Public API reference](docs/api/public-api-reference.md)
- [BaseAPIView](docs/api/base-api-view.md) · [Search](docs/api/search.md) · [Filters & pagination](docs/api/filters-pagination.md)
- [Permissions](docs/security/permissions.md)
- [Soft delete](docs/features/soft-delete.md) · [Files & PDF](docs/features/files-pdf.md)
- [Creating a new resource](docs/development/creating-resource.md) · [Management commands](docs/development/management-commands.md)
- [The hr app](docs/hr/overview.md)
- [Git Flow & releases](docs/deployment/releases.md)
- [Troubleshooting](docs/troubleshooting/common-errors.md)

---

## 🚀 Roadmap

- [ ] Stripe integration
- [ ] Billing dashboard
- [ ] Resource auto-router
- [ ] Action auditing
- [ ] Multi-tenant logs
- [ ] Permission cache (Redis)

---

## 🤝 Contributing

Pull requests are welcome. For larger changes, please open an issue first to discuss direction.

```bash
git clone https://github.com/metanochava/django_resaas.git
cd django_resaas
pip install -e .
make check
```

---

## 📄 License

Distributed under the [MIT](LICENSE) license.

---

<div align="center">

Made by **[Metano Chavana](https://github.com/metanochava)**

</div>
