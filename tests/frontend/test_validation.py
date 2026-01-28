# tests/frontend/test_validation.py
"""
Tests para funciones de validación puras.

Estas funciones son puras (sin efectos secundarios) y fáciles de testear,
siguiendo el principio de "Separación de Responsabilidades" de la Guía General.
"""

from sam.web.frontend.utils.validation import validate_robot_data


class TestValidateRobotData:
    """Tests para la función validate_robot_data."""

    def test_valid_robot_data(self):
        """Test que valida datos de robot correctos."""
        data = {
            "Robot": "Test Robot",
            "MinEquipos": 1,
            "MaxEquipos": 5,
            "PrioridadBalanceo": 10,
        }
        result = validate_robot_data(data)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_missing_robot_name(self):
        """Test que detecta nombre de robot faltante."""
        data = {
            "Robot": "",
            "MinEquipos": 1,
            "MaxEquipos": 5,
        }
        result = validate_robot_data(data)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "nombre del robot" in result.errors[0].lower()

    def test_missing_robot_name_whitespace(self):
        """Test que detecta nombre de robot con solo espacios."""
        data = {
            "Robot": "   ",
            "MinEquipos": 1,
            "MaxEquipos": 5,
        }
        result = validate_robot_data(data)

        assert result.is_valid is False
        assert "nombre del robot" in result.errors[0].lower()

    def test_missing_numeric_fields(self):
        """Test que detecta campos numéricos faltantes."""
        data = {
            "Robot": "Test Robot",
            # Faltan MinEquipos, MaxEquipos, PrioridadBalanceo
        }
        result = validate_robot_data(data)

        assert result.is_valid is False
        assert len(result.errors) == 3
        assert any("MinEquipos" in error for error in result.errors)
        assert any("MaxEquipos" in error for error in result.errors)
        assert any("PrioridadBalanceo" in error for error in result.errors)

    def test_invalid_numeric_fields(self):
        """Test que detecta campos numéricos con valores inválidos."""
        data = {
            "Robot": "Test Robot",
            "MinEquipos": "not a number",
            "MaxEquipos": None,
            "PrioridadBalanceo": 10,
        }
        result = validate_robot_data(data)

        assert result.is_valid is False
        assert len(result.errors) >= 2
        assert any("MinEquipos" in error for error in result.errors)
        assert any("MaxEquipos" in error for error in result.errors)

    def test_multiple_errors(self):
        """Test que acumula múltiples errores."""
        data = {
            "Robot": "",
            "MinEquipos": "invalid",
        }
        result = validate_robot_data(data)

        assert result.is_valid is False
        assert len(result.errors) >= 2

    def test_valid_with_optional_fields(self):
        """Test que acepta campos opcionales adicionales."""
        data = {
            "Robot": "Test Robot",
            "MinEquipos": 1,
            "MaxEquipos": 5,
            "PrioridadBalanceo": 10,
            "Descripcion": "Optional description",
            "Activo": True,
        }
        result = validate_robot_data(data)

        assert result.is_valid is True
        assert len(result.errors) == 0
