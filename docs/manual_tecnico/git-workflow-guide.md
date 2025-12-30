# Guía de Mejores Prácticas - Flujo de Trabajo con Git

## 1. Configuración Inicial

### Configuración básica de Git
```bash
# Configurar identidad
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"

# Editor por defecto (opcional)
git config --global core.editor "code --wait"

# Visualización de colores
git config --global color.ui auto
```

### Inicializar repositorio
```bash
# Crear nuevo repositorio
git init

# O clonar existente
git clone <url-repositorio>
```

### Configurar múltiples remotos (GitHub + GitLab)
```bash
# Agregar GitHub como remoto principal
git remote add origin https://github.com/usuario/proyecto.git

# Agregar GitLab como remoto secundario
git remote add gitlab https://gitlab.com/usuario/proyecto.git

# Verificar remotos configurados
git remote -v
```

## 2. Estrategia de Branching Simplificada

### Estructura de branches
- **main**: Código en producción, siempre estable
- **develop**: Desarrollo activo, integración de features
- **feature/nombre-feature**: Para desarrollar nuevas características (cuando sea necesario)

### Crear y cambiar entre branches
```bash
# Crear branch develop desde main
git checkout -b develop

# Crear feature branch desde develop
git checkout -b feature/nueva-funcionalidad

# Cambiar entre branches
git checkout develop
git checkout main

# Listar branches
git branch
```

## 3. Convención de Commits

### Formato de mensaje
```
<tipo>: <descripción corta>

[Descripción detallada opcional]
```

### Tipos de commits
- **feat**: Nueva funcionalidad
- **fix**: Corrección de bug
- **docs**: Cambios en documentación
- **style**: Formato, puntos y comas, sin cambios de código
- **refactor**: Refactorización de código
- **test**: Agregar o modificar tests
- **chore**: Tareas de mantenimiento, configuración

### Ejemplos
```bash
git commit -m "feat: agregar endpoint de autenticación"
git commit -m "fix: corregir error en validación de formulario"
git commit -m "docs: actualizar README con instrucciones de instalación"
git commit -m "refactor: simplificar lógica de procesamiento de datos"
```

## 4. Versionado Semántico (SemVer)

### Formato: MAJOR.MINOR.PATCH (ej: 1.2.3)

- **MAJOR** (1.0.0): Cambios incompatibles con versiones anteriores
- **MINOR** (0.1.0): Nueva funcionalidad compatible con versiones anteriores
- **PATCH** (0.0.1): Correcciones de bugs compatibles

### Ejemplos prácticos
- `1.0.0` → `1.0.1`: Arreglaste un bug
- `1.0.1` → `1.1.0`: Agregaste una nueva feature
- `1.1.0` → `2.0.0`: Cambiaste la API o algo que rompe compatibilidad

### Crear tags de versión
```bash
# Crear tag anotado (recomendado)
git tag -a v1.0.0 -m "Release version 1.0.0"

# Listar tags
git tag

# Ver información de un tag
git show v1.0.0

# Push de tags a remotos
git push origin v1.0.0
git push gitlab v1.0.0

# Push de todos los tags
git push origin --tags
git push gitlab --tags
```

## 5. Flujo de Trabajo Diario

### Proceso típico de desarrollo

#### A. Iniciar nueva feature
```bash
# Asegurarse de estar actualizado
git checkout develop
git pull origin develop

# Crear branch para la feature
git checkout -b feature/mi-nueva-feature
```

#### B. Trabajar en la feature
```bash
# Ver estado de archivos
git status

# Agregar cambios al staging
git add archivo.py
git add .  # Agregar todos los archivos modificados

# Hacer commit
git commit -m "feat: implementar nueva funcionalidad X"

# Commits frecuentes (recomendado)
git add .
git commit -m "feat: agregar validación de entrada"
git commit -m "feat: completar lógica de procesamiento"
```

#### C. Finalizar feature y mergear
```bash
# Cambiar a develop
git checkout develop

# Mergear feature
git merge feature/mi-nueva-feature

# Eliminar branch de feature (opcional)
git branch -d feature/mi-nueva-feature
```

#### D. Sincronizar con remotos
```bash
# Push a GitHub
git push origin develop

# Push a GitLab
git push gitlab develop

# Push de ambos a la vez (crear alias)
git push origin develop && git push gitlab develop
```

### Crear release desde develop
```bash
# Cambiar a main
git checkout main

# Mergear develop en main
git merge develop

# Crear tag de versión
git tag -a v1.2.0 -m "Release 1.2.0: descripción de cambios"

# Push a ambos remotos
git push origin main
git push gitlab main
git push origin --tags
git push gitlab --tags
```

## 6. Comandos Esenciales

### Comandos diarios
```bash
# Ver estado actual
git status

# Ver historial de commits
git log --oneline --graph --all

# Ver diferencias antes de commit
git diff

# Ver diferencias de staged files
git diff --staged

# Deshacer cambios en archivo (antes de add)
git checkout -- archivo.py

# Quitar archivo del staging (después de add)
git reset HEAD archivo.py

# Ver branches
git branch -a
```

### Git Stash - Guardar cambios temporalmente

El stash es útil cuando tienes cambios sin commitear y necesitas cambiar de branch rápidamente.

```bash
# Guardar cambios actuales en stash
git stash

# Guardar con mensaje descriptivo (recomendado)
git stash save "trabajo en proceso de feature X"

# Ver lista de stashes guardados
git stash list
# Salida: stash@{0}: On develop: trabajo en proceso de feature X
#         stash@{1}: WIP on develop: mensaje anterior

# Aplicar último stash y eliminarlo de la lista
git stash pop

# Aplicar último stash pero mantenerlo en la lista
git stash apply

# Aplicar un stash específico
git stash apply stash@{1}

# Ver contenido de un stash
git stash show -p

# Eliminar último stash sin aplicar
git stash drop

# Eliminar un stash específico
git stash drop stash@{1}

# Limpiar todos los stashes
git stash clear
```

#### Ejemplo de uso común
```bash
# Estás trabajando en develop con cambios sin commitear
git status  # Archivos modificados

# Necesitas urgente revisar algo en main
git stash save "cambios de API en proceso"

# Cambias de branch sin problemas
git checkout main
# ... revisas lo que necesitabas ...

# Vuelves a develop y recuperas tu trabajo
git checkout develop
git stash pop  # Tus cambios vuelven y se eliminan del stash
```

### Sincronización
```bash
# Actualizar desde remoto
git pull origin develop

# Push a remoto
git push origin develop

# Push a ambos remotos
git push origin develop && git push gitlab develop

# Fetch para ver cambios sin aplicar
git fetch origin
```

### Alias útiles (configuración global)
```bash
# Crear aliases para comandos frecuentes
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.cm commit
git config --global alias.lg "log --oneline --graph --all"

# Alias para push a ambos remotos
git config --global alias.pushall '!git push origin && git push gitlab'
```

## 7. Troubleshooting Común

### Conflictos al hacer merge
```bash
# Git marcará los archivos en conflicto
# Editar archivos manualmente y resolver conflictos
# Buscar marcadores: <<<<<<<, =======, >>>>>>>

# Después de resolver
git add archivo-resuelto.py
git commit -m "merge: resolver conflictos de merge"
```

### Deshacer último commit (sin perder cambios)
```bash
git reset --soft HEAD~1
```

### Deshacer último commit (perdiendo cambios)
```bash
git reset --hard HEAD~1
```

### Ver qué cambió en un commit específico
```bash
git show <hash-commit>
```

### Recuperar archivo de commit anterior
```bash
git checkout <hash-commit> -- archivo.py
```

## 8. Buenas Prácticas

### ✅ Hacer
- Commits pequeños y frecuentes
- Mensajes de commit descriptivos
- Pull antes de push
- Usar branches para features nuevas
- Taggear releases importantes
- Mantener main siempre estable
- Revisar cambios antes de commit (`git diff`)

### ❌ Evitar
- Commits gigantes con muchos cambios
- Mensajes vagos ("fix", "update", "cambios")
- Trabajar directamente en main
- Push sin pull previo
- Commit de archivos sensibles (contraseñas, tokens)
- Reescribir historia en branches compartidos

## 9. Checklist Pre-Commit

Antes de cada commit, verifica:
- [ ] `git status` - ¿Estoy commiteando lo correcto?
- [ ] `git diff` - ¿Los cambios son los esperados?
- [ ] ¿El código funciona correctamente?
- [ ] ¿No incluyo archivos sensibles o temporales?
- [ ] ¿El mensaje de commit es descriptivo?

## 10. Flujo Rápido de Referencia

### Desarrollo normal
```bash
git checkout develop
git pull origin develop
# ... hacer cambios ...
git add .
git commit -m "tipo: descripción"
git push origin develop && git push gitlab develop
```

### Crear release
```bash
git checkout main
git merge develop
git tag -a v1.x.x -m "Release 1.x.x"
git push origin main && git push gitlab main
git push origin --tags && git push gitlab --tags
git checkout develop
```

---

## Recursos Adicionales

- **Ver historial visual**: `git log --oneline --graph --all`
- **Ayuda de comando**: `git help <comando>`
- **Documentación oficial**: https://git-scm.com/doc
