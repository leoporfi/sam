# ============================================================================
# EJEMPLOS DE CÓDIGO - SAM WEB SERVICE
# ============================================================================
# Este archivo contiene ejemplos completos de implementación para features
# críticas del servicio web de SAM
# ============================================================================

# ============================================================================
# EJEMPLO 1: VALIDACIÓN DE REGLA BR-001
# No permitir programar robots con EsOnline=1
# ============================================================================

# --- Backend: Validación en endpoint ---
# Archivo: src/web/backend/api.py

from fastapi import HTTPException


@router.post("/api/programaciones", tags=["Programaciones"])
async def create_schedule_with_validation(
    data: ScheduleData, 
    db: DatabaseConnector = Depends(get_db)
):
    """
    Crea una nueva programación validando BR-001.
    """
    try:
        # VALIDACIÓN BR-001: Verificar que el robot NO esté Online
        query_check = "SELECT EsOnline, Activo FROM dbo.Robots WHERE RobotId = ?"
        robot_status = db.ejecutar_consulta(query_check, (data.RobotId,), es_select=True)
        
        if not robot_status:
            raise HTTPException(
                status_code=404, 
                detail=f"Robot con ID {data.RobotId} no encontrado."
            )
        
        robot = robot_status[0]
        
        if robot["EsOnline"]:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No se puede crear una programación para un robot en modo Online. "
                    "Por favor, desactive el modo Online primero (EsOnline debe ser 0)."
                )
            )
        
        if not robot["Activo"]:
            raise HTTPException(
                status_code=400,
                detail="No se puede programar un robot inactivo. Active el robot primero."
            )
        
        # Si pasa las validaciones, proceder con la creación
        db_service.create_new_schedule(db, data)
        return {"message": "Programación creada con éxito."}
        
    except HTTPException:
        raise  # Re-lanzar HTTPException sin envolver
    except Exception as e:
        logger.error(f"Error al crear programación: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al crear programación: {str(e)}")


# --- Frontend: Validación preventiva en modal ---
# Archivo: src/web/frontend/features/modals/dashboard_modal_components.py

@component
def SchedulesModal(robot: Dict[str, Any] | None, on_close: Callable, on_save_success: Callable):
    """
    Modal de programaciones con validación preventiva de BR-001.
    """
    notification_ctx = use_context(NotificationContext)
    show_notification = notification_ctx["show_notification"]
    
    # Validación preventiva: mostrar advertencia si el robot está Online
    @use_effect(dependencies=[robot])
    def check_robot_status():
        if robot and robot.get("EsOnline"):
            show_notification(
                "ADVERTENCIA: Este robot está en modo Online. Debe desactivar el modo Online "
                "antes de crear una programación.",
                "warning"
            )
    
    async def submit_form(event):
        # Doble validación antes de enviar
        if robot.get("EsOnline"):
            show_notification(
                "No se puede programar un robot en modo Online. "
                "Cambie EsOnline a 0 primero.",
                "error"
            )
            return
        
        # Proceder con el envío...
        try:
            await api_service.create_schedule(payload)
            show_notification("Programación creada con éxito.", "success")
            await on_save_success()
        except APIException as e:
            show_notification(str(e), "error")


# ============================================================================
# EJEMPLO 2: DASHBOARD DE PERFORMANCE DEL BALANCEADOR
# Visualización en tiempo real del servicio Balanceador
# ============================================================================

# --- Backend: Nuevo endpoint para métricas ---
# Archivo: src/web/backend/api.py

@router.get("/api/dashboards/balanceador", tags=["Dashboards"])
async def get_balanceador_dashboard(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    pool_id: Optional[int] = Query(None),
    db: DatabaseConnector = Depends(get_db)
):
    """
    Obtiene métricas del dashboard del balanceador.
    Usa el SP ObtenerDashboardBalanceador.
    """
    try:
        # Establecer fechas por defecto (últimos 7 días)
        if not fecha_inicio:
            fecha_inicio = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not fecha_fin:
            fecha_fin = datetime.now().strftime("%Y-%m-%d")
        
        # Llamar al stored procedure que retorna múltiples result sets
        query = "EXEC dbo.ObtenerDashboardBalanceador @FechaInicio=?, @FechaFin=?, @PoolId=?"
        params = (fecha_inicio, fecha_fin, pool_id)
        
        # Procesar múltiples result sets
        metrics = {}
        with db.obtener_cursor() as cursor:
            cursor.execute(query, params)
            
            # Result Set 1: Métricas generales
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            if row:
                metrics["general"] = dict(zip(columns, row))
            
            # Result Set 2: Trazabilidad (gráfico)
            if cursor.nextset():
                columns = [col[0] for col in cursor.description]
                metrics["trazabilidad"] = [
                    dict(zip(columns, row)) for row in cursor.fetchall()
                ]
            
            # Result Set 3: Resumen diario
            if cursor.nextset():
                columns = [col[0] for col in cursor.description]
                metrics["resumen_diario"] = [
                    dict(zip(columns, row)) for row in cursor.fetchall()
                ]
            
            # Result Set 4: Análisis por robot
            if cursor.nextset():
                columns = [col[0] for col in cursor.description]
                metrics["analisis_robots"] = [
                    dict(zip(columns, row)) for row in cursor.fetchall()
                ]
            
            # Result Set 5: Estado actual
            if cursor.nextset():
                columns = [col[0] for col in cursor.description]
                row = cursor.fetchone()
                if row:
                    metrics["estado_actual"] = dict(zip(columns, row))
            
            # Result Set 6: Thrashing events
            if cursor.nextset():
                columns = [col[0] for col in cursor.description]
                row = cursor.fetchone()
                if row:
                    metrics["thrashing"] = dict(zip(columns, row))
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error al obtener dashboard del balanceador: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Error al obtener métricas: {str(e)}"
        )


# --- Frontend: Componente Dashboard ---
# Archivo: src/web/frontend/features/dashboards/balanceador_dashboard.py

from reactpy import component, html, use_effect, use_state

from ...api_client import get_api_client
from ...shared.common_components import LoadingSpinner


@component
def BalanceadorDashboard():
    """
    Dashboard de performance del servicio Balanceador.
    """
    metrics, set_metrics = use_state(None)
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)
    
    # Filtros
    fecha_inicio, set_fecha_inicio = use_state("")
    fecha_fin, set_fecha_fin = use_state("")
    pool_id, set_pool_id = use_state(None)
    
    api_client = get_api_client()
    
    @use_effect(dependencies=[fecha_inicio, fecha_fin, pool_id])
    async def fetch_metrics():
        set_loading(True)
        set_error(None)
        try:
            params = {}
            if fecha_inicio:
                params["fecha_inicio"] = fecha_inicio
            if fecha_fin:
                params["fecha_fin"] = fecha_fin
            if pool_id:
                params["pool_id"] = pool_id
            
            data = await api_client._request("GET", "/api/dashboards/balanceador", params=params)
            set_metrics(data)
        except Exception as e:
            set_error(str(e))
        finally:
            set_loading(False)
    
    if loading:
        return LoadingSpinner()
    
    if error:
        return html.article({"aria-invalid": "true"}, f"Error: {error}")
    
    if not metrics:
        return html.article("No hay datos disponibles.")
    
    general = metrics.get("general", {})
    estado = metrics.get("estado_actual", {})
    
    return html.section(
        html.h2("Dashboard del Balanceador"),
        
        # Filtros
        html.article(
            html.div(
                {"className": "grid"},
                html.label(
                    "Fecha Inicio",
                    html.input({
                        "type": "date",
                        "value": fecha_inicio,
                        "onChange": lambda e: set_fecha_inicio(e["target"]["value"])
                    })
                ),
                html.label(
                    "Fecha Fin",
                    html.input({
                        "type": "date",
                        "value": fecha_fin,
                        "onChange": lambda e: set_fecha_fin(e["target"]["value"])
                    })
                )
            )
        ),
        
        # KPIs principales
        html.div(
            {"className": "grid"},
            KPICard("Total Acciones", general.get("TotalAcciones", 0), "primary"),
            KPICard("Asignaciones", general.get("TotalAsignaciones", 0), "green"),
            KPICard("Desasignaciones", general.get("TotalDesasignaciones", 0), "amber"),
            KPICard("Robots Afectados", general.get("RobotsAfectados", 0), "azure")
        ),
        
        # Estado actual del sistema
        html.article(
            html.h3("Estado Actual del Sistema"),
            html.div(
                {"className": "grid"},
                html.p(html.strong("Robots Activos: "), estado.get("RobotsActivos", 0)),
                html.p(html.strong("Robots Online: "), estado.get("RobotsOnline", 0)),
                html.p(html.strong("Equipos Activos: "), estado.get("EquiposActivos", 0)),
                html.p(html.strong("Equipos Balanceables: "), estado.get("EquiposBalanceables", 0))
            )
        ),
        
        # Tabla de análisis por robot
        html.article(
            html.h3("Análisis por Robot"),
            RobotAnalysisTable(metrics.get("analisis_robots", []))
        ),
        
        # Gráfico de tendencia (simulado con tabla por ahora)
        html.article(
            html.h3("Tendencia Diaria"),
            DailyTrendTable(metrics.get("resumen_diario", []))
        )
    )


@component
def KPICard(title: str, value: int, color: str = "primary"):
    """Tarjeta KPI estilizada."""
    return html.article(
        {"className": f"pico-background-{color}-500", "style": {"textAlign": "center"}},
        html.h6(title),
        html.h2(str(value))
    )


@component
def RobotAnalysisTable(data: list):
    """Tabla de análisis por robot."""
    if not data:
        return html.p("No hay datos disponibles.")
    
    return html.table(
        html.thead(
            html.tr(
                html.th("Robot"),
                html.th("Total Acciones"),
                html.th("Asignaciones"),
                html.th("Desasignaciones"),
                html.th("Prom. Tickets"),
                html.th("Última Acción")
            )
        ),
        html.tbody(
            *[
                html.tr(
                    html.td(row.get("RobotNombre", "N/A")),
                    html.td(row.get("TotalAcciones", 0)),
                    html.td(row.get("Asignaciones", 0)),
                    html.td(row.get("Desasignaciones", 0)),
                    html.td(f"{row.get('PromedioTickets', 0):.1f}"),
                    html.td(row.get("UltimaAccion", "N/A")[:16] if row.get("UltimaAccion") else "N/A")
                )
                for row in data[:10]  # Top 10
            ]
        )
    )


@component
def DailyTrendTable(data: list):
    """Tabla de tendencia diaria."""
    if not data:
        return html.p("No hay datos disponibles.")
    
    return html.table(
        html.thead(
            html.tr(
                html.th("Fecha"),
                html.th("Total Acciones"),
                html.th("Asignaciones"),
                html.th("Desasignaciones"),
                html.th("Prom. Tickets")
            )
        ),
        html.tbody(
            *[
                html.tr(
                    html.td(row.get("Fecha", "N/A")),
                    html.td(row.get("TotalAcciones", 0)),
                    html.td(row.get("Asignaciones", 0)),
                    html.td(row.get("Desasignaciones", 0)),
                    html.td(f"{row.get('PromedioTickets', 0):.1f}")
                )
                for row in data
            ]
        )
    )


# ============================================================================
# EJEMPLO 3: SISTEMA DE AUDITORÍA (AUDIT LOG)
# Registro automático de operaciones CRUD
# ============================================================================

# --- Base de Datos: Nueva tabla ---
# Archivo: audit_log_schema.sql

"""
CREATE TABLE dbo.AuditLog (
    AuditId INT IDENTITY(1,1) PRIMARY KEY,
    Timestamp DATETIME2(0) NOT NULL DEFAULT GETDATE(),
    Usuario NVARCHAR(100) NOT NULL,
    Operacion NVARCHAR(20) NOT NULL, -- CREATE, UPDATE, DELETE
    EntidadTipo NVARCHAR(50) NOT NULL, -- Robot, Programacion, Pool, etc.
    EntidadId INT NOT NULL,
    EntidadNombre NVARCHAR(200) NULL,
    ValoresAnteriores NVARCHAR(MAX) NULL, -- JSON
    ValoresNuevos NVARCHAR(MAX) NULL, -- JSON
    DireccionIP NVARCHAR(50) NULL,
    UserAgent NVARCHAR(500) NULL
);

CREATE INDEX IX_AuditLog_Timestamp ON dbo.AuditLog(Timestamp DESC);
CREATE INDEX IX_AuditLog_EntidadTipo_EntidadId ON dbo.AuditLog(EntidadTipo, EntidadId);
"""


# --- Backend: Decorator para auditoría automática ---
# Archivo: src/web/backend/audit.py

import json
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional

from fastapi import Request


class AuditLogger:
    """
    Gestor de auditoría para operaciones CRUD.
    """
    
    def __init__(self, db_connector):
        self.db = db_connector
    
    def log(
        self,
        usuario: str,
        operacion: str,
        entidad_tipo: str,
        entidad_id: int,
        entidad_nombre: Optional[str] = None,
        valores_anteriores: Optional[Dict] = None,
        valores_nuevos: Optional[Dict] = None,
        direccion_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Registra una operación en el audit log."""
        try:
            query = """
            INSERT INTO dbo.AuditLog 
            (Usuario, Operacion, EntidadTipo, EntidadId, EntidadNombre, 
             ValoresAnteriores, ValoresNuevos, DireccionIP, UserAgent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                usuario,
                operacion,
                entidad_tipo,
                entidad_id,
                entidad_nombre,
                json.dumps(valores_anteriores) if valores_anteriores else None,
                json.dumps(valores_nuevos) if valores_nuevos else None,
                direccion_ip,
                user_agent
            )
            
            self.db.ejecutar_consulta(query, params, es_select=False)
            
        except Exception as e:
            # Nunca fallar la operación principal por un error de auditoría
            logger.error(f"Error al registrar en audit log: {e}", exc_info=True)


def audit_operation(
    entidad_tipo: str,
    operacion: str,
    get_entidad_id: Callable[[Any], int],
    get_entidad_nombre: Optional[Callable[[Any], str]] = None,
    get_valores_anteriores: Optional[Callable[[Any], Dict]] = None
):
    """
    Decorator para auditar automáticamente operaciones CRUD.
    
    Ejemplo de uso:
    @audit_operation(
        entidad_tipo="Robot",
        operacion="UPDATE",
        get_entidad_id=lambda kwargs: kwargs.get("robot_id"),
        get_entidad_nombre=lambda kwargs: f"Robot {kwargs.get('robot_id')}",
        get_valores_anteriores=lambda kwargs: get_robot_current_values(kwargs.get("robot_id"))
    )
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Obtener request y db de los argumentos
            request: Optional[Request] = kwargs.get("request")
            db = kwargs.get("db")
            
            # Obtener valores anteriores si está definido
            valores_anteriores = None
            if get_valores_anteriores:
                try:
                    valores_anteriores = get_valores_anteriores(kwargs)
                except Exception:
                    pass
            
            # Ejecutar la operación principal
            result = await func(*args, **kwargs)
            
            # Registrar en audit log después de éxito
            if db:
                audit_logger = AuditLogger(db)
                
                entidad_id = get_entidad_id(kwargs)
                entidad_nombre = get_entidad_nombre(kwargs) if get_entidad_nombre else None
                
                # Obtener valores nuevos del resultado o de los parámetros
                valores_nuevos = None
                if operacion == "UPDATE":
                    valores_nuevos = kwargs.get("robot_data") or kwargs.get("pool_data") or {}
                elif operacion == "CREATE":
                    valores_nuevos = result if isinstance(result, dict) else {}
                
                audit_logger.log(
                    usuario=request.client.host if request else "system",
                    operacion=operacion,
                    entidad_tipo=entidad_tipo,
                    entidad_id=entidad_id,
                    entidad_nombre=entidad_nombre,
                    valores_anteriores=valores_anteriores,
                    valores_nuevos=valores_nuevos,
                    direccion_ip=request.client.host if request else None,
                    user_agent=request.headers.get("user-agent") if request else None
                )
            
            return result
        
        return wrapper
    return decorator


# --- Backend: Uso del decorator en endpoints ---
# Archivo: src/web/backend/api.py

@router.put("/api/robots/{robot_id}", tags=["Robots"])
@audit_operation(
    entidad_tipo="Robot",
    operacion="UPDATE",
    get_entidad_id=lambda kwargs: kwargs.get("robot_id"),
    get_entidad_nombre=lambda kwargs: f"Robot ID {kwargs.get('robot_id')}",
    get_valores_anteriores=lambda kwargs: get_robot_for_audit(kwargs.get("db"), kwargs.get("robot_id"))
)
async def update_robot_details_with_audit(
    robot_id: int, 
    robot_data: RobotUpdateRequest,
    request: Request,  # Añadir para obtener IP y User-Agent
    db: DatabaseConnector = Depends(get_db)
):
    """
    Actualiza un robot y registra la operación en audit log.
    """
    try:
        updated_count = db_service.update_robot_details(db, robot_id, robot_data)
        if updated_count > 0:
            return {"message": f"Robot {robot_id} actualizado con éxito."}
        else:
            raise HTTPException(status_code=404, detail="Robot no encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_robot_for_audit(db: DatabaseConnector, robot_id: int) -> Dict:
    """Helper para obtener estado actual del robot para auditoría."""
    query = "SELECT * FROM dbo.Robots WHERE RobotId = ?"
    result = db.ejecutar_consulta(query, (robot_id,), es_select=True)
    return result[0] if result else {}


# --- Backend: Endpoint para consultar audit log ---
@router.get("/api/audit", tags=["Audit"])
async def get_audit_log(
    entidad_tipo: Optional[str] = Query(None),
    entidad_id: Optional[int] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: DatabaseConnector = Depends(get_db)
):
    """
    Obtiene registros del audit log con filtros.
    """
    try:
        conditions = []
        params = []
        
        if entidad_tipo:
            conditions.append("EntidadTipo = ?")
            params.append(entidad_tipo)
        
        if entidad_id:
            conditions.append("EntidadId = ?")
            params.append(entidad_id)
        
        if fecha_inicio:
            conditions.append("Timestamp >= ?")
            params.append(fecha_inicio)
        
        if fecha_fin:
            conditions.append("Timestamp <= ?")
            params.append(fecha_fin)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Count total
        count_query = f"SELECT COUNT(*) as total FROM dbo.AuditLog {where_clause}"
        total = db.ejecutar_consulta(count_query, tuple(params), es_select=True)[0]["total"]
        
        # Get page
        offset = (page - 1) * size
        query = f"""
        SELECT AuditId, Timestamp, Usuario, Operacion, EntidadTipo, 
               EntidadId, EntidadNombre, ValoresAnteriores, ValoresNuevos
        FROM dbo.AuditLog
        {where_clause}
        ORDER BY Timestamp DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        params.extend([offset, size])
        
        records = db.ejecutar_consulta(query, tuple(params), es_select=True)
        
        return {
            "total_count": total,
            "page": page,
            "size": size,
            "records": records
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EJEMPLO 4: VALIDACIÓN AVANZADA DE PROGRAMACIONES
# Validación de campos condicionales según TipoProgramacion
# ============================================================================

# --- Backend: Validador personalizado en Pydantic ---
# Archivo: src/web/backend/schemas.py

from datetime import date, time
from typing import List, Optional

from pydantic import BaseModel, root_validator, validator


class ScheduleData(BaseModel):
    RobotId: int
    TipoProgramacion: str
    HoraInicio: str  # Formato "HH:MM"
    Tolerancia: int
    Equipos: List[int]
    DiasSemana: Optional[str] = None
    DiaDelMes: Optional[int] = None
    FechaEspecifica: Optional[str] = None  # Formato "YYYY-MM-DD"
    
    @validator("TipoProgramacion")
    def validate_tipo(cls, v):
        """Valida que el tipo de programación sea válido."""
        valid_types = ["Diaria", "Semanal", "Mensual", "Especifica"]
        if v not in valid_types:
            raise ValueError(
                f"TipoProgramacion debe ser uno de: {', '.join(valid_types)}"
            )
        return v
    
    @validator("Tolerancia")
    def validate_tolerancia(cls, v):
        """Valida que la tolerancia esté en rango válido."""
        if not (0 <= v <= 1440):
            raise ValueError("Tolerancia debe estar entre 0 y 1440 minutos (24 horas)")
        return v
    
    @validator("Equipos")
    def validate_equipos(cls, v):
        """Valida que haya al menos un equipo."""
        if not v or len(v) == 0:
            raise ValueError("Debe seleccionar al menos un equipo")
        return v
    
    @validator("DiasSemana")
    def validate_dias_semana(cls, v):
        """Valida formato de días de la semana."""
        if v:
            valid_days = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"]
            days = [d.strip() for d in v.split(",")]
            invalid = [d for d in days if d not in valid_days]
            if invalid:
                raise ValueError(
                    f"Días inválidos: {', '.join(invalid)}. "
                    f"Use: {', '.join(valid_days)}"
                )
        return v
    
    @validator("DiaDelMes")
    def validate_dia_del_mes(cls, v):
        """Valida que el día del mes sea válido."""
        if v is not None and not (1 <= v <= 31):
            raise ValueError("DiaDelMes debe estar entre 1 y 31")
        return v
    
    @root_validator
    def validate_conditional_fields(cls, values):
        """
        Validación cruzada: verifica que los campos requeridos estén presentes
        según el TipoProgramacion.
        """
        tipo = values.get("TipoProgramacion")
        
        if tipo == "Semanal":
            if not values.get("DiasSemana"):
                raise ValueError(
                    "DiasSemana es requerido para programaciones Semanales. "
                    "Formato: 'Lu,Ma,Mi,Ju,Vi'"
                )
        
        elif tipo == "Mensual":
            if not values.get("DiaDelMes"):
                raise ValueError(
                    "DiaDelMes es requerido para programaciones Mensuales. "
                    "Debe ser un número entre 1 y 31"
                )
        
        elif tipo == "Especifica":
            if not values.get("FechaEspecifica"):
                raise ValueError(
                    "FechaEspecifica es requerida para programaciones Específicas. "
                    "Formato: 'YYYY-MM-DD'"
                )
            
            # Validar formato de fecha
            try:
                fecha_parts = values.get("FechaEspecifica").split("-")
                if len(fecha_parts) != 3:
                    raise ValueError()
                date(int(fecha_parts[0]), int(fecha_parts[1]), int(fecha_parts[2]))
            except (ValueError, AttributeError):
                raise ValueError(
                    "FechaEspecifica debe estar en formato 'YYYY-MM-DD'"
                )
        
        # Validar formato de HoraInicio
        try:
            hora_parts = values.get("HoraInicio", "").split(":")
            if len(hora_parts) != 2:
                raise ValueError()
            time(int(hora_parts[0]), int(hora_parts[1]))
        except (ValueError, AttributeError):
            raise ValueError(
                "HoraInicio debe estar en formato 'HH:MM' (24 horas)"
            )
        
        return values


# ============================================================================
# EJEMPLO 5: MANEJO DE ERRORES MEJORADO
# Custom exception handlers para errores descriptivos
# ============================================================================

# --- Backend: Exception handlers personalizados ---
# Archivo: src/web/backend/exceptions.py

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class SAMBusinessRuleException(Exception):
    """Excepción personalizada para violaciones de reglas de negocio."""
    def __init__(self, rule_id: str, message: str, details: dict = None):
        self.rule_id = rule_id
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


async def business_rule_exception_handler(request: Request, exc: SAMBusinessRuleException):
    """Handler para errores de reglas de negocio."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "business_rule_violation",
            "rule_id": exc.rule_id,
            "message": exc.message,
            "details": exc.details,
            "suggestion": get_suggestion_for_rule(exc.rule_id)
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler mejorado para errores de validación de Pydantic."""
    errors_formatted = []
    
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_type = error["type"]
        
        # Mensajes personalizados según el tipo de error
        user_friendly_message = message
        if error_type == "value_error.missing":
            user_friendly_message = f"El campo '{field}' es requerido"
        elif error_type == "type_error.integer":
            user_friendly_message = f"El campo '{field}' debe ser un número entero"
        elif error_type == "value_error.list.min_items":
            user_friendly_message = f"El campo '{field}' debe tener al menos un elemento"
        
        errors_formatted.append({
            "field": field,
            "message": user_friendly_message,
            "type": error_type
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Los datos proporcionados no son válidos",
            "errors": errors_formatted
        }
    )


def get_suggestion_for_rule(rule_id: str) -> str:
    """Retorna sugerencias útiles según la regla violada."""
    suggestions = {
        "BR-001": "Desactive el modo Online del robot (EsOnline=0) antes de crear una programación.",
        "BR-003": "Las asignaciones manuales se marcarán automáticamente como reservadas.",
        "BR-006": "Espere a que finalice la ejecución actual antes de desasignar el equipo.",
        "BR-010": "Seleccione al menos un equipo antes de guardar la programación."
    }
    return suggestions.get(rule_id, "Verifique los datos e intente nuevamente.")


# --- Backend: Uso en endpoints ---
# Archivo: src/web/run_interfaz_web.py o main.py

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from backend.exceptions import (SAMBusinessRuleException,
                                business_rule_exception_handler,
                                validation_exception_handler)

app = FastAPI(title="SAM Web Interface")

# Registrar exception handlers
app.add_exception_handler(SAMBusinessRuleException, business_rule_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Ejemplo de uso en endpoint
@router.patch("/api/robots/{robot_id}", tags=["Robots"])
async def update_robot_status(
    robot_id: int, 
    updates: Dict[str, bool] = Body(...), 
    db: DatabaseConnector = Depends(get_db)
):
    try:
        field_to_update = next(iter(updates))
        
        # Validación BR-001: No permitir EsOnline=1 si tiene programaciones
        if field_to_update == "EsOnline" and updates[field_to_update] == True:
            query_check = """
            SELECT COUNT(*) as count 
            FROM dbo.Programaciones 
            WHERE RobotId = ? AND Activo = 1
            """
            result = db.ejecutar_consulta(query_check, (robot_id,), es_select=True)
            
            if result[0]["count"] > 0:
                raise SAMBusinessRuleException(
                    rule_id="BR-001",
                    message="No se puede activar el modo Online porque el robot tiene programaciones activas.",
                    details={
                        "robot_id": robot_id,
                        "programaciones_activas": result[0]["count"]
                    }
                )
        
        success = db_service.update_robot_status(db, robot_id, field_to_update, updates[field_to_update])
        if success:
            return {"message": "Estado del robot actualizado con éxito."}
        raise HTTPException(status_code=404, detail="Robot no encontrado.")
        
    except SAMBusinessRuleException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EJEMPLO 6: HOOK PERSONALIZADO PARA GESTIÓN DE ESTADO
# Hook reutilizable con filtros, paginación y ordenamiento
# ============================================================================

# --- Frontend: Custom hook genérico ---
# Archivo: src/web/frontend/hooks/use_paginated_data.py

from typing import Any, Callable, Dict

from reactpy import use_callback, use_effect, use_state


def use_paginated_data(
    fetch_function: Callable,
    initial_filters: Dict[str, Any] = None,
    initial_page: int = 1,
    initial_size: int = 20,
    initial_sort_by: str = None,
    initial_sort_dir: str = "asc"
):
    """
    Hook reutilizable para gestionar datos paginados con filtros y ordenamiento.
    
    Args:
        fetch_function: Función async que retorna los datos
        initial_filters: Filtros iniciales
        initial_page: Página inicial
        initial_size: Tamaño de página inicial
        initial_sort_by: Campo de ordenamiento inicial
        initial_sort_dir: Dirección de ordenamiento inicial
    
    Returns:
        Dict con datos, estados y funciones de control
    """
    # Estados
    data, set_data = use_state([])
    loading, set_loading = use_state(True)
    error, set_error = use_state(None)
    total_count, set_total_count = use_state(0)
    
    # Parámetros de paginación
    current_page, set_current_page = use_state(initial_page)
    page_size, set_page_size = use_state(initial_size)
    
    # Parámetros de ordenamiento
    sort_by, set_sort_by = use_state(initial_sort_by)
    sort_dir, set_sort_dir = use_state(initial_sort_dir)
    
    # Parámetros de filtrado
    filters, set_filters = use_state(initial_filters or {})
    
    # Función para refrescar datos
    @use_callback
    async def refresh():
        set_loading(True)
        set_error(None)
        try:
            # Construir parámetros
            params = {
                **filters,
                "page": current_page,
                "size": page_size
            }
            
            if sort_by:
                params["sort_by"] = sort_by
                params["sort_dir"] = sort_dir
            
            # Fetch data
            result = await fetch_function(params)
            
            # Actualizar estados
            set_data(result.get("data") or result.get("robots") or result.get("pools") or [])
            set_total_count(result.get("total_count", 0))
            
        except Exception as e:
            set_error(str(e))
        finally:
            set_loading(False)
    
    # Efecto para cargar datos cuando cambian los parámetros
    @use_effect(dependencies=[current_page, page_size, sort_by, sort_dir, filters])
    def load_data():
        import asyncio
        task = asyncio.create_task(refresh())
        return lambda: task.cancel()
    
    # Función para cambiar ordenamiento
    @use_callback
    def handle_sort(field: str):
        if sort_by == field:
            # Alternar dirección
            set_sort_dir("desc" if sort_dir == "asc" else "asc")
        else:
            # Nuevo campo, ordenar ascendente
            set_sort_by(field)
            set_sort_dir("asc")
    
    # Calcular total de páginas
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    
    return {
        # Datos
        "data": data,
        "loading": loading,
        "error": error,
        "total_count": total_count,
        
        # Paginación
        "current_page": current_page,
        "page_size": page_size,
        "total_pages": total_pages,
        "set_current_page": set_current_page,
        "set_page_size": set_page_size,
        
        # Ordenamiento
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "handle_sort": handle_sort,
        
        # Filtros
        "filters": filters,
        "set_filters": set_filters,
        
        # Acciones
        "refresh": refresh
    }


# --- Frontend: Uso del hook en componente ---
# Archivo: src/web/frontend/features/dashboard/robot_list.py

from reactpy import component, html

from ...api_client import get_api_client
from ...hooks.use_paginated_data import use_paginated_data


@component
def RobotListWithPagination():
    """
    Lista de robots usando el hook genérico de paginación.
    """
    api_client = get_api_client()
    
    # Usar el hook genérico
    state = use_paginated_data(
        fetch_function=api_client.get_robots,
        initial_filters={"active": None, "online": None},
        initial_page=1,
        initial_size=20,
        initial_sort_by="Robot",
        initial_sort_dir="asc"
    )
    
    # Renderizar UI
    if state["loading"] and not state["data"]:
        return html.article({"aria-busy": "true"}, "Cargando datos...")
    
    if state["error"]:
        return html.article({"aria-invalid": "true"}, f"Error: {state['error']}")
    
    return html.section(
        html.h2("Lista de Robots"),
        
        # Filtros
        html.div(
            {"className": "grid"},
            html.select(
                {
                    "value": str(state["filters"].get("active", "all")),
                    "onChange": lambda e: state["set_filters"](
                        {**state["filters"], "active": None if e["target"]["value"] == "all" else e["target"]["value"] == "true"}
                    )
                },
                html.option({"value": "all"}, "Todos"),
                html.option({"value": "true"}, "Activos"),
                html.option({"value": "false"}, "Inactivos")
            )
        ),
        
        # Tabla con datos
        html.table(
            html.thead(
                html.tr(
                    html.th(
                        html.a(
                            {"href": "#", "onClick": lambda e: state["handle_sort"]("Robot")},
                            "Robot",
                            " ▲" if state["sort_by"] == "Robot" and state["sort_dir"] == "asc" else " ▼" if state["sort_by"] == "Robot" else ""
                        )
                    ),
                    html.th("Activo"),
                    html.th("Online")
                )
            ),
            html.tbody(
                *[
                    html.tr(
                        html.td(robot["Robot"]),
                        html.td(str(robot["Activo"])),
                        html.td(str(robot["EsOnline"]))
                    )
                    for robot in state["data"]
                ]
            )
        ),
        
        # Paginación
        html.nav(
            {"className": "grid"},
            html.button(
                {
                    "disabled": state["current_page"] == 1,
                    "onClick": lambda e: state["set_current_page"](state["current_page"] - 1)
                },
                "Anterior"
            ),
            html.span(f"Página {state['current_page']} de {state['total_pages']}"),
            html.button(
                {
                    "disabled": state["current_page"] == state["total_pages"],
                    "onClick": lambda e: state["set_current_page"](state["current_page"] + 1)
                },
                "Siguiente"
            )
        )
    )


# ============================================================================
# EJEMPLO 7: TESTS UNITARIOS CON PYTEST
# Tests para validaciones y reglas de negocio
# ============================================================================

# --- Tests: Archivo de pruebas ---
# Archivo: tests/test_business_rules.py

from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from src.web.backend.api import router
from src.web.backend.exceptions import SAMBusinessRuleException
from src.web.backend.schemas import ScheduleData


# Fixtures
@pytest.fixture
def mock_db():
    """Mock del DatabaseConnector."""
    db = Mock()
    db.ejecutar_consulta = Mock()
    return db


@pytest.fixture
def test_client():
    """Cliente de prueba para FastAPI."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# Tests de validación de schemas
class TestScheduleDataValidation:
    """Tests para validaciones de ScheduleData."""
    
    def test_valid_daily_schedule(self):
        """Programación diaria válida."""
        data = ScheduleData(
            RobotId=1,
            TipoProgramacion="Diaria",
            HoraInicio="09:00",
            Tolerancia=60,
            Equipos=[1, 2, 3]
        )
        assert data.TipoProgramacion == "Diaria"
        assert data.Equipos == [1, 2, 3]
    
    def test_weekly_schedule_requires_dias_semana(self):
        """Programación semanal requiere DiasSemana."""
        with pytest.raises(ValueError, match="DiasSemana es requerido"):
            ScheduleData(
                RobotId=1,
                TipoProgramacion="Semanal",
                HoraInicio="09:00",
                Tolerancia=60,
                Equipos=[1, 2]
                # Falta DiasSemana
            )
    
    def test_monthly_schedule_requires_dia_del_mes(self):
        """Programación mensual requiere DiaDelMes."""
        with pytest.raises(ValueError, match="DiaDelMes es requerido"):
            ScheduleData(
                RobotId=1,
                TipoProgramacion="Mensual",
                HoraInicio="09:00",
                Tolerancia=60,
                Equipos=[1]
                # Falta DiaDelMes
            )
    
    def test_invalid_tipo_programacion(self):
        """Tipo de programación inválido."""
        with pytest.raises(ValueError, match="TipoProgramacion debe ser uno de"):
            ScheduleData(
                RobotId=1,
                TipoProgramacion="Trimestral",  # Inválido
                HoraInicio="09:00",
                Tolerancia=60,
                Equipos=[1]
            )
    
    def test_tolerancia_out_of_range(self):
        """Tolerancia fuera de rango."""
        with pytest.raises(ValueError, match="Tolerancia debe estar entre"):
            ScheduleData(
                RobotId=1,
                TipoProgramacion="Diaria",
                HoraInicio="09:00",
                Tolerancia=2000,  # Mayor a 1440
                Equipos=[1]
            )
    
    def test_empty_equipos_list(self):
        """Lista de equipos vacía."""
        with pytest.raises(ValueError, match="al menos un equipo"):
            ScheduleData(
                RobotId=1,
                TipoProgramacion="Diaria",
                HoraInicio="09:00",
                Tolerancia=60,
                Equipos=[]  # Vacío
            )


# Tests de reglas de negocio
class TestBusinessRuleBR001:
    """Tests para BR-001: No programar robots Online."""
    
    def test_cannot_create_schedule_for_online_robot(self, mock_db):
        """No se puede programar un robot con EsOnline=1."""
        # Mock: robot está Online
        mock_db.ejecutar_consulta.return_value = [{"EsOnline": True, "Activo": True}]
        
        # Importar función del endpoint
        from src.web.backend.api import create_schedule_with_validation
        
        schedule_data = ScheduleData(
            RobotId=1,
            TipoProgramacion="Diaria",
            HoraInicio="09:00",
            Tolerancia=60,
            Equipos=[1, 2]
        )
        
        # Debe lanzar HTTPException
        with pytest.raises(Exception) as exc_info:
            import asyncio
            asyncio.run(create_schedule_with_validation(schedule_data, mock_db))
        
        assert "modo Online" in str(exc_info.value)
    
    def test_can_create_schedule_for_offline_robot(self, mock_db):
        """Se puede programar un robot con EsOnline=0."""
        # Mock: robot está Offline y Activo
        mock_db.ejecutar_consulta.side_effect = [
            [{"EsOnline": False, "Activo": True}],  # Verificación
            None  # Creación exitosa
        ]
        
        from src.web.backend.api import create_schedule_with_validation
        
        schedule_data = ScheduleData(
            RobotId=1,
            TipoProgramacion="Diaria",
            HoraInicio="09:00",
            Tolerancia=60,
            Equipos=[1, 2]
        )
        
        # No debe lanzar excepción
        import asyncio
        result = asyncio.run(create_schedule_with_validation(schedule_data, mock_db))
        
        assert result["message"] == "Programación creada con éxito."


# Tests de integración con API
class TestRobotEndpoints:
    """Tests de integración para endpoints de robots."""
    
    @patch('src.web.backend.database.get_robots')
    def test_get_robots_endpoint(self, mock_get_robots, test_client):
        """Test del endpoint GET /api/robots."""
        # Mock de respuesta
        mock_get_robots.return_value = {
            "total_count": 2,
            "page": 1,
            "size": 20,
            "robots": [
                {"RobotId": 1, "Robot": "Test Robot 1", "Activo": True},
                {"RobotId": 2, "Robot": "Test Robot 2", "Activo": False}
            ]
        }
        
        # Hacer request
        response = test_client.get("/api/robots")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["robots"]) == 2
    
    @patch('src.web.backend.database.update_robot_status')
    def test_update_robot_status_endpoint(self, mock_update, test_client):
        """Test del endpoint PATCH /api/robots/{id}."""
        mock_update.return_value = True
        
        response = test_client.patch(
            "/api/robots/1",
            json={"Activo": False}
        )
        
        assert response.status_code == 200
        assert "actualizado" in response.json()["message"]


# Comando para ejecutar tests:
# pytest tests/ -v --cov=src/web/backend --cov-report=html


# ============================================================================
# EJEMPLO 8: CONFIGURACIÓN DE PRODUCCIÓN
# Setup completo para deployment con NSSM
# ============================================================================

# --- Script de instalación del servicio ---
# Archivo: install_service.ps1

"""
# Script PowerShell para instalar SAM Web Interface como servicio de Windows

# Variables de configuración
$ServiceName = "SAM-InterfazWeb"
$DisplayName = "SAM - Interfaz Web de Gestión RPA"
$Description = "Servicio web para gestión de robots RPA del sistema SAM"
$ProjectRoot = "C:\RPA\SAM"
$PythonExe = "C:\RPA\SAM\venv\Scripts\python.exe"
$StartScript = "$ProjectRoot\src\web\run_interfaz_web.py"
$LogDir = "C:\RPA\Logs\SAM"

# Crear directorio de logs si no existe
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force
    Write-Host "Directorio de logs creado: $LogDir"
}

# Verificar que NSSM esté instalado
$NssmPath = "C:\Tools\nssm.exe"
if (-not (Test-Path $NssmPath)) {
    Write-Host "ERROR: NSSM no encontrado en $NssmPath"
    Write-Host "Descargue NSSM desde: https://nssm.cc/download"
    exit 1
}

# Detener y eliminar servicio existente si existe
$ExistingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($ExistingService) {
    Write-Host "Deteniendo servicio existente..."
    Stop-Service -Name $ServiceName -Force
    & $NssmPath remove $ServiceName confirm
    Start-Sleep -Seconds 2
}

# Instalar nuevo servicio
Write-Host "Instalando servicio $ServiceName..."
& $NssmPath install $ServiceName $PythonExe $StartScript

# Configurar parámetros del servicio
& $NssmPath set $ServiceName DisplayName $DisplayName
& $NssmPath set $ServiceName Description $Description
& $NssmPath set $ServiceName AppDirectory $ProjectRoot
& $NssmPath set $ServiceName AppStdout "$LogDir\service_stdout.log"
& $NssmPath set $ServiceName AppStderr "$LogDir\service_stderr.log"
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateBytes 10485760  # 10MB
& $NssmPath set $ServiceName AppRotateOnline 1

# Configurar inicio automático
& $NssmPath set $ServiceName Start SERVICE_AUTO_START

# Configurar reinicio en caso de fallo
& $NssmPath set $ServiceName AppExit Default Restart
& $NssmPath set $ServiceName AppRestartDelay 5000  # 5 segundos

# Iniciar servicio
Write-Host "Iniciando servicio..."
Start-Service -Name $ServiceName

# Verificar estado
$ServiceStatus = Get-Service -Name $ServiceName
Write-Host "`nServicio instalado exitosamente!"
Write-Host "Estado: $($ServiceStatus.Status)"
Write-Host "Logs: $LogDir"
Write-Host "URL: http://localhost:8000"
"""


# --- Archivo de configuración de producción ---
# Archivo: .env.production

"""
# Configuración de producción para SAM Web Interface

# Base de datos
SQL_SAM_HOST=SERVIDOR_PRODUCCION
SQL_SAM_DB_NAME=SAM_PROD
SQL_SAM_UID=sam_web_user
SQL_SAM_PWD=<PASSWORD_SEGURO>
SQL_SAM_DRIVER={ODBC Driver 17 for SQL Server}

# Automation Anywhere A360
AA_CR_URL=https://control-room.automationanywhere.com
AA_CR_USER=api_user@domain.com
AA_CR_API_KEY=<API_KEY_SEGURO>
AA_VERIFY_SSL=True

# Servicio Web
INTERFAZ_WEB_HOST=0.0.0.0
INTERFAZ_WEB_PORT=8000
INTERFAZ_WEB_DEBUG=False

# Logging
LOG_DIRECTORY=C:/RPA/Logs/SAM
LOG_LEVEL=INFO
LOG_BACKUP_COUNT=30

# Seguridad (cuando se implemente)
# JWT_SECRET_KEY=<GENERAR_KEY_SEGURA>
# JWT_ALGORITHM=HS256
# JWT_EXPIRATION_MINUTES=60
"""

# ============================================================================
# FIN DE EJEMPLOS
# ============================================================================

print("Ejemplos de código generados exitosamente.")
print("Revise cada sección para implementación en su proyecto SAM.")# JWT_SECRET_KEY=<GENERAR_KEY_SEGURA>
# JWT_ALGORITHM=HS256
# JWT_EXPIRATION_MINUTES=60
"""

# ============================================================================
# FIN DE EJEMPLOS
# ============================================================================

print("Ejemplos de código generados exitosamente.")
print("Revise cada sección para implementación en su proyecto SAM.")