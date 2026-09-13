"""code_validator.validate_vue()/validate_javascript() - the Node
subprocess path (esbuild + @vue/compiler-sfc). Needs a real frontend
project's node_modules to actually exercise (this library itself has
no front/ sibling - see workspace_service.get_workspace_roots()'s
FRONTEND_PROJECT_DIR fallback), so these tests point
settings.FRONTEND_PROJECT_DIR at the real dev/front checkout instead of
relying on the library's own (nonexistent) one. Skipped automatically
if that checkout isn't present in this environment (CI-safe)."""
from pathlib import Path

import pytest

from django_resaas.saas.management.apicommands.service import code_validator

DEV_FRONT = Path("/var/www/dev/front")

pytestmark = pytest.mark.skipif(
    not (DEV_FRONT / "node_modules" / "esbuild").exists(),
    reason="No real frontend node_modules (esbuild/@vue/compiler-sfc) available in this environment",
)


@pytest.fixture(autouse=True)
def _point_at_real_frontend(settings):
    settings.FRONTEND_PROJECT_DIR = str(DEV_FRONT)


class TestValidateJavascript:

    def test_valid_js_passes(self):
        result = code_validator.validate_javascript("const x = 1\nexport default x\n")
        assert result["valid"] is True, result["errors"]

    def test_syntax_error_is_blocked(self):
        result = code_validator.validate_javascript("const x = ;\n")
        assert result["valid"] is False
        assert result["errors"]


class TestValidateVue:

    def test_valid_sfc_passes(self):
        content = (
            "<template><div>{{ msg }}</div></template>\n"
            "<script setup>\nconst msg = 'hi'\n</script>\n"
        )
        result = code_validator.validate_vue(content)
        assert result["valid"] is True, result["errors"]

    def test_unclosed_tag_is_blocked(self):
        """mega-prompt secção 28: unclosed tags devem ser detectados."""
        content = "<template><div>{{ msg }}</template>\n<script setup>\nconst msg = 1\n</script>\n"
        result = code_validator.validate_vue(content)
        assert result["valid"] is False
        assert result["errors"]

    def test_broken_script_syntax_is_blocked(self):
        content = "<template><div /></template>\n<script setup>\nconst x = (\n</script>\n"
        result = code_validator.validate_vue(content)
        assert result["valid"] is False
