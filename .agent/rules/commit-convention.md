---
trigger: always_on
---

# 📝 Convención de Commits y Versionado

Para mantener el historial limpio y el control de versiones preciso, sigue estas reglas:

### 1. Mensaje de Commit
**IMPORTANTE: El mensaje debe estar escrito obligatoriamente en ESPAÑOL.**

Usa los siguientes prefijos según el tipo de cambio:
- `feat:` Nuevas funcionalidades.
- `fix:` Corrección de errores.
- `docs:` Cambios solo en documentación.
- `db:` Cambios en Stored Procedures, tablas o migraciones.
- `refactor:` Cambios en el código que no corrigen errores ni añaden funciones.
- `test:` Añadir o modificar tests.

### 2. Versionado Semántico (SemVer)
Si el commit es de tipo `feat:` o `fix:`, es **OBLIGATORIO** incrementar la versión en [src/sam/__init__.py](cci:7://file:///c:/Users/lporfiri/RPA/sam/src/sam/__init__.py:0:0-0:0):
- `feat:` → Incrementa **MINOR** (ej: 1.9.1 → 1.10.0).
- `fix:` → Incrementa **PATCH** (ej: 1.9.1 → 1.9.2).

### 3. Etiquetas (Tags)
Para hitos importantes o releases:
- Crear un tag anotado: `git tag -a vX.Y.Z -m "Release version X.Y.Z"`
- Subir los tags al remoto: `git push origin --tags`
