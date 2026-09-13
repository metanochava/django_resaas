"""code_validator.py - the pipeline IDEWorkspaceAPIView.write/apply and
ScaffoldAPIView.create() both call before writing anything to disk.
Unit-level: no HTTP, no filesystem - just feeding content strings
straight to the validators."""
from django_resaas.saas.management.apicommands.service import code_validator


class TestDetectLanguage:

    def test_detects_by_extension(self):
        assert code_validator.detect_language("models/paciente.py") == "python"
        assert code_validator.detect_language("PacienteLPage.vue") == "vue"
        assert code_validator.detect_language("store.js") == "javascript"
        assert code_validator.detect_language("schema.json") == "json"
        assert code_validator.detect_language("deploy.sh") == "shell"
        assert code_validator.detect_language("README") == "plaintext"


class TestValidatePython:

    def test_valid_syntax_passes(self):
        result = code_validator.validate_python("x = 1\nprint(x)\n", check_imports=False)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_syntax_error_is_blocked(self):
        """mega-prompt secção 132: "def foo(" deve bloquear Save."""
        result = code_validator.validate_python("def foo(\n", check_imports=False)

        assert result["valid"] is False
        assert result["errors"]
        assert result["errors"][0]["line"] is not None

    def test_unclosed_class_is_blocked(self):
        result = code_validator.validate_python("class User(\n", check_imports=False)
        assert result["valid"] is False

    def test_real_stdlib_import_passes(self):
        result = code_validator.validate_python("import os\nfrom os import path\n")
        assert result["valid"] is True
        assert result["errors"] == []

    def test_missing_module_is_blocked(self):
        """mega-prompt secção 133: "from module_that_does_not_exist
        import Foo" deve dar erro."""
        result = code_validator.validate_python(
            "from module_that_does_not_exist import Foo\n"
        )

        assert result["valid"] is False
        assert "module_that_does_not_exist" in result["errors"][0]["message"]

    def test_missing_name_in_real_module_is_blocked(self):
        result = code_validator.validate_python(
            "from os import this_name_does_not_exist_in_os\n"
        )

        assert result["valid"] is False
        assert "this_name_does_not_exist_in_os" in result["errors"][0]["message"]

    def test_relative_import_is_never_hard_blocked(self):
        """Import relativo não é resolvível por find_spec() sem o
        pacote completo carregado - nunca deve virar um false-positive
        bloqueante."""
        result = code_validator.validate_python("from . import models\n")
        assert result["valid"] is True

    def test_check_imports_false_skips_import_validation(self):
        result = code_validator.validate_python(
            "from totally_fake_module import Nothing\n", check_imports=False,
        )
        assert result["valid"] is True


class TestValidateJson:

    def test_valid_json_passes(self):
        assert code_validator.validate_json('{"a": 1}')["valid"] is True

    def test_invalid_json_is_blocked(self):
        result = code_validator.validate_json('{"a": }')
        assert result["valid"] is False
        assert result["errors"]


class TestValidateShell:

    def test_valid_shell_passes(self):
        result = code_validator.validate_shell("#!/bin/bash\necho hi\n")
        assert result["valid"] is True

    def test_invalid_shell_is_blocked(self):
        result = code_validator.validate_shell("if [ true; then\necho oops\n")
        assert result["valid"] is False


class TestValidateFileDispatch:

    def test_unknown_extension_never_blocks(self):
        """Sem validador para .md/.css - nunca bloqueia por não
        conseguirmos verificar, apenas informa."""
        result = code_validator.validate_file("README.md", "# whatever ((( not markdown")
        assert result["valid"] is True
        assert result["language"] == "markdown"

    def test_python_file_routes_to_python_validator(self):
        result = code_validator.validate_file("models/x.py", "def broken(\n")
        assert result["valid"] is False
        assert result["language"] == "python"

    def test_json_file_routes_to_json_validator(self):
        result = code_validator.validate_file("schema.json", "{not valid}")
        assert result["valid"] is False
        assert result["language"] == "json"
