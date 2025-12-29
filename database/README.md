# Base de Datos - Estructura y Scripts

Este directorio contiene la estructura completa de la base de datos SAM exportada desde SQL Server.

## 📁 Estructura

```
database/
├── tables/          # Tablas (CREATE TABLE)
├── views/           # Vistas
├── procedures/      # Stored Procedures
├── functions/       # Funciones definidas por el usuario
├── triggers/        # Triggers
└── export_db_ssms_like.ps1  # Script de exportación
```

## 🔄 Exportar Estructura

Para exportar la estructura actual de la base de datos:

```powershell
.\database\export_db_ssms_like.ps1
```

**Requisitos:**
- Módulo `SqlServer` de PowerShell instalado: `Install-Module SqlServer`
- Variables de entorno en `.env`:
  - `SQL_SERVER`
  - `SQL_DATABASE`
  - `SQL_USER`
  - `SQL_PASSWORD`

## 📝 Convenciones

- **Nomenclatura**: `Schema_ObjectName.sql` (ej: `dbo_Programaciones.sql`)
- **Formato**: UTF-8 con BOM
- **Opciones**: Similar a SSMS (IncludeIfNotExists, SchemaQualify, etc.)

## 🔍 Uso

### Buscar un objeto específico
```powershell
# Buscar tabla
Get-ChildItem database\tables\*Programaciones*

# Buscar stored procedure
Get-ChildItem database\procedures\*CrearProgramacion*
```

### Comparar cambios
```bash
# Ver qué cambió en un objeto
git diff database/procedures/dbo_CrearProgramacion.sql
```

### Restaurar estructura completa
Los scripts están listos para ejecutar en orden:
1. `tables/` - Primero las tablas
2. `views/` - Luego las vistas
3. `procedures/` - Después los procedimientos
4. `functions/` - Finalmente las funciones

## ⚠️ Notas

- **Solo estructura**: Este export NO incluye datos, solo el esquema
- **Backup de datos**: Usar `BACKUP DATABASE` para datos
- **Versionado**: Los archivos están versionados en Git para seguimiento de cambios

