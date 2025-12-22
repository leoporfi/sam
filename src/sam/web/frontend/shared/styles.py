# sam/web/frontend/shared/styles.py
"""
Constantes centralizadas para clases CSS reutilizables.

Este módulo mantiene consistencia visual en toda la aplicación definiendo
clases CSS reutilizables siguiendo el estándar de ReactPy de SAM.

Uso:
    from sam.web.frontend.shared.styles import BUTTON_PRIMARY, STATUS_RUNNING

    html.button(
        {"class_name": BUTTON_PRIMARY},
        "Guardar"
    )
"""

# ============================================================================
# BOTONES
# ============================================================================

# Botones principales (PicoCSS)
BUTTON_PRIMARY = "btn btn-primary"
BUTTON_SECONDARY = "btn btn-secondary"
BUTTON_DANGER = "btn btn-danger"
BUTTON_OUTLINE = "btn outline"
BUTTON_OUTLINE_SECONDARY = "btn outline secondary"
BUTTON_OUTLINE_DANGER = "btn outline danger"

# ============================================================================
# ESTADOS Y BADGES
# ============================================================================

# Estados de robots/equipos (usando tags de PicoCSS)
STATUS_RUNNING = "tag"
STATUS_STOPPED = "tag secondary"
STATUS_UNKNOWN = "tag"
STATUS_COOLING = "tag"

# Estados de ejecución
STATUS_EJECUCION_PROGRAMADO = "tag tag-ejecucion-programado"
STATUS_EJECUCION_DEMANDA = "tag tag-ejecucion-demanda"

# Tags genéricos
TAG = "tag"
TAG_SECONDARY = "tag secondary"

# ============================================================================
# LAYOUT Y CONTENEDORES
# ============================================================================

# Contenedores principales
CONTAINER = "container"
CARD = "card"
GRID = "grid"

# Contenedores específicos
CARDS_CONTAINER = "cards-container"
CARDS_CONTAINER_ROBOTS = "cards-container robot-cards"
CARDS_CONTAINER_POOLS = "cards-container pool-cards"
TABLE_CONTAINER = "table-container"

# ============================================================================
# COMPONENTES ESPECÍFICOS
# ============================================================================

# Cards
ROBOT_CARD = "robot-card"
ROBOT_CARD_HEADER = "robot-card-header"
ROBOT_CARD_BODY = "robot-card-body"
ROBOT_CARD_FOOTER = "robot-card-footer"

POOL_CARD = "pool-card"
POOL_CARD_HEADER = "pool-card-header"
POOL_CARD_BODY = "pool-card-body"
POOL_CARD_FOOTER = "pool-card-footer"

SCHEDULE_CARD = "schedule-card"

# Controles
DASHBOARD_CONTROLS = "dashboard-controls"
CONTROLS_HEADER = "controls-header"
MASTER_CONTROLS_GRID = "master-controls-grid"
COLLAPSIBLE_PANEL = "collapsible-panel"
COLLAPSIBLE_PANEL_EXPANDED = "collapsible-panel is-expanded"
MOBILE_CONTROLS_TOGGLE = "mobile-controls-toggle outline secondary"

# Búsqueda
SEARCH_INPUT = "search-input"

# ============================================================================
# UTILIDADES
# ============================================================================

# Clases de utilidad comunes
CLICKABLE = "clickable"
OUTLINE = "outline"
SECONDARY = "secondary"
PRIMARY = "primary"
