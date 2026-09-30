# django_resaas Documentation

This folder contains the technical documentation for the `django_resaas`
backend framework.

## Navigation

-   [Installation](getting-started/installation.md)
-   [Quick start](getting-started/quick-start.md)
-   [Architecture](architecture/overview.md)
-   [Multi-tenancy](architecture/multi-tenancy.md)
-   [Request lifecycle](architecture/request-lifecycle.md)
-   [Middleware](architecture/middleware.md)
-   [View registry](architecture/registry.md)
-   [Dynamic dashboards saas](architecture/dashboards.md)
-   [Models and RESAAS](models/resaas-config.md)
-   [Schema 1.0 contract](api/schema-contract.md)
-   [Public API reference](api/public-api-reference.md)
-   [BaseAPIView](api/base-api-view.md)
-   [Errors and alerts](api/errors-and-alerts.md)
-   [Search](api/search.md)
-   [Filters and pagination](api/filters-pagination.md)
-   [Permissions](security/permissions.md)
-   [Field-level permissions](security/field-permissions.md)
-   [Soft delete](features/soft-delete.md)
-   [Files and PDF](features/files-pdf.md)
-   [Notifications (Email/SMS/WhatsApp)](features/notifications.md)
-   [Public sites and their contact form](features/public-sites.md)
-   [Creating a new resource](development/creating-resource.md)
-   [Building a module](development/building-a-module.md)
-   [Minimal example app](../src/dev/README.md)
-   [Management commands](development/management-commands.md)
-   [Consolidation progress](development/consolidation-progress.md)
-   [Git flow and releases](deployment/releases.md)
-   [Upgrading (shipped migrations)](deployment/upgrading.md)
-   [Troubleshooting](troubleshooting/common-errors.md)

## Purpose

`django_resaas` provides a reusable base for Django/DRF applications with
CRUD, multi-tenancy, permissions, search, filters, dynamic serialization
and other common features.
