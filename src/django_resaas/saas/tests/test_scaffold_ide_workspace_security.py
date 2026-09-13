"""workspace_service.py - path safety (traversal/absolute/denylist) and
the IDEWorkspaceAPIView endpoints built on top of it. Covers mega-
prompt secções 14/94/131 explicitly: "../../../etc/passwd", absolute
path escape, .env/denylisted files."""
from pathlib import Path

import pytest

from django_resaas.saas.management.apicommands.service import workspace_service
from django_resaas.saas.management.apicommands.service.workspace_service import WorkspaceError

pytestmark = pytest.mark.django_db


class TestResolveSafePath:

    def test_unknown_root_is_rejected(self):
        with pytest.raises(WorkspaceError) as exc:
            workspace_service.resolve_safe_path("does_not_exist", "foo.py")
        assert exc.value.code == "unknown_root"

    def test_path_traversal_is_rejected(self, settings):
        roots = workspace_service.get_workspace_roots()
        assert roots, "expected at least one real workspace root (settings.MY_APPS)"
        root_key = next(iter(roots))

        with pytest.raises(WorkspaceError) as exc:
            workspace_service.resolve_safe_path(root_key, "../../../../../../etc/passwd")
        assert exc.value.code == "path_traversal"

    def test_absolute_path_is_neutralized_into_the_root(self):
        """A leading "/" is stripped before joining (rel_path.lstrip("/"))
        - "/etc/passwd" never reaches the real /etc/passwd, it resolves
        to "<root>/etc/passwd" (almost certainly non-existent, but
        still safely inside the sandbox, never outside it)."""
        roots = workspace_service.get_workspace_roots()
        root_key = next(iter(roots))
        root = roots[root_key]

        resolved = workspace_service.resolve_safe_path(root_key, "/etc/passwd")

        assert resolved.is_relative_to(root)
        assert resolved != Path("/etc/passwd")

    def test_dotenv_is_denied(self):
        roots = workspace_service.get_workspace_roots()
        root_key = next(iter(roots))

        with pytest.raises(WorkspaceError) as exc:
            workspace_service.resolve_safe_path(root_key, ".env")
        assert exc.value.code == "denied"

    def test_pem_file_is_denied(self):
        roots = workspace_service.get_workspace_roots()
        root_key = next(iter(roots))

        with pytest.raises(WorkspaceError) as exc:
            workspace_service.resolve_safe_path(root_key, "certs/server.pem")
        assert exc.value.code == "denied"

    def test_plain_relative_path_within_root_is_allowed(self):
        roots = workspace_service.get_workspace_roots()
        root_key = next(iter(roots))

        path = workspace_service.resolve_safe_path(root_key, "models/__init__.py")
        assert str(path).endswith("models/__init__.py") or str(path).endswith("models\\__init__.py")

    def test_frontend_root_is_registered_when_present(self):
        roots = workspace_service.get_workspace_roots()
        # Neste ambiente de testes (biblioteca), não existe um sibling
        # front/ real, então "frontend" pode legitimamente estar
        # ausente - apenas confirma que, quando presente, resolve para
        # um Path real.
        if "frontend" in roots:
            assert roots["frontend"].exists()


class TestIDEWorkspaceEndpointsSecurity:

    def test_tree_blocks_unknown_root(self, bootstrap_tenant, settings):
        settings.DEBUG = True
        tenant = bootstrap_tenant("ide-tree-unknown-root")
        tenant["user"].is_staff = True
        tenant["user"].save()
        client = tenant["client"]

        response = client.get("/api/django_resaas/ide/tree/?root=does_not_exist")
        assert response.status_code == 400

    def test_read_blocks_path_traversal(self, bootstrap_tenant, settings):
        settings.DEBUG = True
        tenant = bootstrap_tenant("ide-read-traversal")
        tenant["user"].is_staff = True
        tenant["user"].save()
        client = tenant["client"]

        roots = workspace_service.get_workspace_roots()
        root_key = next(iter(roots))

        response = client.get(
            f"/api/django_resaas/ide/read/?root={root_key}&path=../../../../../../etc/passwd"
        )
        assert response.status_code == 400

    def test_read_blocks_dotenv(self, bootstrap_tenant, settings):
        settings.DEBUG = True
        tenant = bootstrap_tenant("ide-read-dotenv")
        tenant["user"].is_staff = True
        tenant["user"].save()
        client = tenant["client"]

        roots = workspace_service.get_workspace_roots()
        root_key = next(iter(roots))

        response = client.get(f"/api/django_resaas/ide/read/?root={root_key}&path=.env")
        assert response.status_code == 400

    def test_disabled_when_not_ide_enabled(self, bootstrap_tenant, settings):
        settings.DEBUG = False
        if hasattr(settings, "SCAFFOLD_IDE_ENABLED"):
            del settings.SCAFFOLD_IDE_ENABLED

        tenant = bootstrap_tenant("ide-disabled")
        tenant["user"].is_staff = True
        tenant["user"].save()
        client = tenant["client"]

        response = client.get("/api/django_resaas/ide/roots/")
        assert response.status_code == 403

    def test_non_staff_user_is_forbidden(self, bootstrap_tenant, settings):
        settings.DEBUG = True
        tenant = bootstrap_tenant("ide-non-staff")
        client = tenant["client"]

        response = client.get("/api/django_resaas/ide/roots/")
        assert response.status_code == 403
