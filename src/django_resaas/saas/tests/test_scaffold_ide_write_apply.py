"""IDEWorkspaceAPIView.write()/apply()/commands()/run() - real HTTP,
real filesystem writes (cleaned up in a fixture teardown - these are
NOT rolled back by Django's test-DB transaction, they are real files).

Covers the mega-prompt's central flow: validate before write, all-
files-or-none for apply(), and optimistic-lock conflict detection."""
import os

import pytest

from django_resaas.saas.management.apicommands.service import workspace_service

pytestmark = pytest.mark.django_db

SCRATCH_ROOT = "django_resaas.hr"
SCRATCH_REL_PATH = "tests/_scaffold_ide_scratch_file.py"
SCRATCH_REL_PATH_2 = "tests/_scaffold_ide_scratch_file_2.py"


@pytest.fixture
def scratch_path():
    path = workspace_service.resolve_safe_path(SCRATCH_ROOT, SCRATCH_REL_PATH)
    yield path
    if path.exists():
        os.unlink(path)


@pytest.fixture
def scratch_path_2():
    path = workspace_service.resolve_safe_path(SCRATCH_ROOT, SCRATCH_REL_PATH_2)
    yield path
    if path.exists():
        os.unlink(path)


@pytest.fixture
def ide_client(bootstrap_tenant, settings):
    settings.DEBUG = True
    tenant = bootstrap_tenant("ide-write-apply")
    tenant["user"].is_staff = True
    tenant["user"].save()
    return tenant["client"]


class TestWrite:

    def test_valid_python_is_written(self, ide_client, scratch_path):
        response = ide_client.post(
            "/api/django_resaas/ide/write/",
            {"root": SCRATCH_ROOT, "path": SCRATCH_REL_PATH, "content": "x = 1\n"},
            format="json",
        )

        assert response.status_code == 200, response.data
        assert scratch_path.exists()
        assert scratch_path.read_text() == "x = 1\n"

    def test_invalid_python_is_never_written(self, ide_client, scratch_path):
        """mega-prompt secção 32: validation.valid === false must block
        write - the file must not exist afterwards."""
        response = ide_client.post(
            "/api/django_resaas/ide/write/",
            {"root": SCRATCH_ROOT, "path": SCRATCH_REL_PATH, "content": "def broken(\n"},
            format="json",
        )

        assert response.status_code == 422
        assert not scratch_path.exists()

    def test_conflict_detected_on_stale_hash(self, ide_client, scratch_path):
        first = ide_client.post(
            "/api/django_resaas/ide/write/",
            {"root": SCRATCH_ROOT, "path": SCRATCH_REL_PATH, "content": "x = 1\n"},
            format="json",
        )
        assert first.status_code == 200

        # Alguém (ou outro separador) muda o ficheiro externamente.
        scratch_path.write_text("x = 999\n")

        second = ide_client.post(
            "/api/django_resaas/ide/write/",
            {
                "root": SCRATCH_ROOT, "path": SCRATCH_REL_PATH, "content": "x = 2\n",
                "expected_hash": first.data["hash"],
            },
            format="json",
        )

        assert second.status_code == 409
        assert scratch_path.read_text() == "x = 999\n"

    def test_path_traversal_is_rejected_at_write(self, ide_client):
        response = ide_client.post(
            "/api/django_resaas/ide/write/",
            {"root": SCRATCH_ROOT, "path": "../../../../../../etc/cron.d/evil", "content": "x = 1\n"},
            format="json",
        )
        assert response.status_code == 400


class TestApply:

    def test_all_valid_files_are_written(self, ide_client, scratch_path, scratch_path_2):
        response = ide_client.post(
            "/api/django_resaas/ide/apply/",
            {"files": [
                {"root": SCRATCH_ROOT, "path": SCRATCH_REL_PATH, "content": "a = 1\n"},
                {"root": SCRATCH_ROOT, "path": SCRATCH_REL_PATH_2, "content": "b = 2\n"},
            ]},
            format="json",
        )

        assert response.status_code == 200, response.data
        assert scratch_path.exists()
        assert scratch_path_2.exists()

    def test_one_invalid_file_blocks_all(self, ide_client, scratch_path, scratch_path_2):
        """mega-prompt secções 38/39/146: multi-file scaffold is
        all-or-nothing - one FAIL blocks every file, including the
        ones that were individually valid."""
        response = ide_client.post(
            "/api/django_resaas/ide/apply/",
            {"files": [
                {"root": SCRATCH_ROOT, "path": SCRATCH_REL_PATH, "content": "a = 1\n"},
                {"root": SCRATCH_ROOT, "path": SCRATCH_REL_PATH_2, "content": "def broken(\n"},
            ]},
            format="json",
        )

        assert response.status_code == 422
        assert not scratch_path.exists()
        assert not scratch_path_2.exists()


class TestValidateEndpointNeverWrites:

    def test_validate_does_not_touch_disk(self, ide_client, scratch_path):
        response = ide_client.post(
            "/api/django_resaas/ide/validate/",
            {"path": SCRATCH_REL_PATH, "content": "x = 1\n"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["valid"] is True
        assert not scratch_path.exists()


class TestCommandsAndRun:

    def test_commands_lists_real_django_check(self, ide_client):
        response = ide_client.get("/api/django_resaas/ide/commands/")

        assert response.status_code == 200
        keys = {c["key"] for c in response.data["commands"]}
        assert "django_check" in keys

    def test_run_rejects_unknown_command(self, ide_client):
        response = ide_client.post(
            "/api/django_resaas/ide/run/", {"key": "rm -rf /"}, format="json",
        )

        assert response.status_code == 200
        assert response.data["ok"] is False

    def test_run_django_check_executes_the_real_command(self, ide_client):
        response = ide_client.post(
            "/api/django_resaas/ide/run/", {"key": "django_check"}, format="json",
        )

        assert response.status_code == 200
        assert response.data["ok"] is True
        assert "issue" in response.data["stdout"].lower()
