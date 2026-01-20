# 🗄️ Validación de Stored Procedures

Cada vez que crees o modifiques un Stored Procedure en `database/procedures/`, DEBES asegurar que cumpla con:

1. **Estructura**:
   - `CREATE OR ALTER PROCEDURE`
   - `SET NOCOUNT ON;`
   - Bloque `BEGIN TRY / END TRY` y `BEGIN CATCH / END CATCH`.
2. **Transacciones**:
   - `BEGIN TRANSACTION` al inicio de la lógica de escritura.
   - `COMMIT TRANSACTION` al final del éxito.
   - `ROLLBACK TRANSACTION` en el bloque `CATCH`.
3. **Manejo de Errores**:
   - Inserción obligatoria en `dbo.ErrorLog` dentro del `CATCH`.
   - Uso de `RAISERROR` o `THROW` para propagar el error a Python.
4. **Nomenclatura**:
   - Nombre en PascalCase (ej: `dbo.ActualizarEstadoRobot`).
   - Parámetros en PascalCase con prefijo `@`.
