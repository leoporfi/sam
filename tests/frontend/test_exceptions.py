# tests/frontend/test_exceptions.py
"""
Tests para excepciones personalizadas.

Verifica que las excepciones se comportan correctamente y proporcionan
información útil para debugging y manejo de errores.
"""

from sam.web.frontend.utils.exceptions import APIException, ValidationException


class TestAPIException:
    """Tests para APIException."""

    def test_basic_exception(self):
        """Test creación básica de APIException."""
        exc = APIException("Test error")

        assert str(exc) == "[API Error]: Test error"
        assert exc.message == "Test error"
        assert exc.status_code is None

    def test_exception_with_status_code(self):
        """Test APIException con código de estado."""
        exc = APIException("Not found", status_code=404)

        assert exc.status_code == 404
        assert "Not found" in str(exc)

    def test_exception_inheritance(self):
        """Test que APIException es una Exception."""
        exc = APIException("Test")

        assert isinstance(exc, Exception)
        assert isinstance(exc, APIException)


class TestValidationException:
    """Tests para ValidationException."""

    def test_basic_exception(self):
        """Test creación básica de ValidationException."""
        exc = ValidationException("Validation failed")

        assert str(exc) == "[Validation Error]: Validation failed - []"
        assert exc.message == "Validation failed"
        assert exc.errors == []

    def test_exception_with_errors(self):
        """Test ValidationException con lista de errores."""
        errors = [
            {"field": "Robot", "message": "Required"},
            {"field": "MinEquipos", "message": "Must be positive"},
        ]
        exc = ValidationException("Validation failed", errors=errors)

        assert exc.errors == errors
        assert "Validation failed" in str(exc)
        assert len(exc.errors) == 2

    def test_exception_inheritance(self):
        """Test que ValidationException es una Exception."""
        exc = ValidationException("Test")

        assert isinstance(exc, Exception)
        assert isinstance(exc, ValidationException)
