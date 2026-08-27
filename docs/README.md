# django_resaas Documentation

This folder contains the technical documentation for the `django_resaas`
backend framework.

## Navigation

-   [Architecture](architecture/overview.md)
-   [Multi-tenancy](architecture/multi-tenancy.md)
-   [Request lifecycle](architecture/request-lifecycle.md)
-   [Middleware](architecture/middleware.md)
-   [Models and RESAAS](models/resaas-config.md)
-   [Schema 1.0 contract](api/schema-contract.md)
-   [Public API reference](api/public-api-reference.md)
-   [BaseAPIView](api/base-api-view.md)
-   [Search](api/search.md)
-   [Filters and pagination](api/filters-pagination.md)
-   [Permissions](security/permissions.md)
-   [Soft delete](features/soft-delete.md)
-   [Files and PDF](features/files-pdf.md)
-   [Creating a new resource](development/creating-resource.md)
-   [Minimal example app](../src/dev/README.md)
-   [Management commands](development/management-commands.md)
-   [The hr app](hr/overview.md)
-   [Git flow and releases](deployment/releases.md)
-   [Troubleshooting](troubleshooting/common-errors.md)

## Purpose

`django_resaas` provides a reusable base for Django/DRF applications with
CRUD, multi-tenancy, permissions, search, filters, dynamic serialization
and other common features.
