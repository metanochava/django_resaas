"""
Regression coverage for the "cannot skip the logo/icon" requirement on
create_root/create_entity: pick_image_file() must never return without a
real, valid image path - not on cancel, not on a missing file, not on a
non-image file. It must keep asking until a valid image is given.
"""
import io

import pytest
from PIL import Image

from django_resaas.saas.core.utils.image_picker import (
    _validate_image_path,
    pick_image_file,
)


@pytest.fixture
def valid_image(tmp_path):
    path = tmp_path / "logo.png"
    Image.new("RGB", (4, 4), color="red").save(path)
    return str(path)


@pytest.fixture
def corrupt_image(tmp_path):
    path = tmp_path / "fake.png"
    path.write_text("this is not actually a png")
    return str(path)


class TestValidateImagePath:
    def test_accepts_a_real_image(self, valid_image):
        path, error = _validate_image_path(valid_image)
        assert path == valid_image
        assert error is None

    def test_rejects_empty_path(self):
        path, error = _validate_image_path("")
        assert path is None
        assert "No file selected" in error

    def test_rejects_missing_file(self, tmp_path):
        missing = str(tmp_path / "does_not_exist.png")
        path, error = _validate_image_path(missing)
        assert path is None
        assert "not found" in error.lower()

    def test_rejects_non_image_extension(self, tmp_path):
        text_file = tmp_path / "notes.txt"
        text_file.write_text("hello")
        path, error = _validate_image_path(str(text_file))
        assert path is None
        assert "supported image type" in error

    def test_rejects_file_with_image_extension_but_invalid_content(self, corrupt_image):
        path, error = _validate_image_path(corrupt_image)
        assert path is None
        assert "not a valid image" in error.lower()


class TestPickImageFileCannotSkip:
    """pick_image_file() is the enforcement point used by create_root.py /
    create_entity.py - it must be impossible to come away with an empty
    or invalid image."""

    def test_returns_the_path_once_a_valid_image_is_given(self, monkeypatch, valid_image):
        # No display/tkinter available -> falls back to the terminal prompt.
        monkeypatch.setattr(
            "django_resaas.saas.core.utils.image_picker._pick_via_dialog",
            lambda title: (_ for _ in ()).throw(RuntimeError("no display")),
        )
        monkeypatch.setattr("builtins.input", lambda *_: valid_image)

        result = pick_image_file("Select a logo")

        assert result == valid_image

    def test_keeps_asking_until_a_valid_image_is_given(self, monkeypatch, tmp_path, valid_image):
        monkeypatch.setattr(
            "django_resaas.saas.core.utils.image_picker._pick_via_dialog",
            lambda title: (_ for _ in ()).throw(RuntimeError("no display")),
        )

        missing = str(tmp_path / "missing.png")
        attempts = iter(["", missing, valid_image])
        monkeypatch.setattr("builtins.input", lambda *_: next(attempts))

        result = pick_image_file("Select a logo")

        assert result == valid_image
        # every bad attempt must actually have been consumed - i.e. the
        # loop really retried instead of accepting the first bad answer
        assert next(attempts, "exhausted") == "exhausted"

    def test_empty_string_from_the_gui_dialog_is_not_accepted(self, monkeypatch, valid_image):
        """User opens the native file dialog and cancels (empty string) -
        must loop back into the dialog, not treat cancel as 'no image'."""
        responses = iter(["", valid_image])
        monkeypatch.setattr(
            "django_resaas.saas.core.utils.image_picker._pick_via_dialog",
            lambda title: next(responses),
        )

        result = pick_image_file("Select a logo")

        assert result == valid_image

    def test_never_returns_a_falsy_value(self, monkeypatch, valid_image):
        monkeypatch.setattr(
            "django_resaas.saas.core.utils.image_picker._pick_via_dialog",
            lambda title: (_ for _ in ()).throw(RuntimeError("no display")),
        )
        monkeypatch.setattr("builtins.input", lambda *_: valid_image)

        result = pick_image_file("Select a logo")

        assert bool(result) is True
