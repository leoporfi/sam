# SAM/Lanzador/tests/manual_integration_test_aa_client.py

import logging
from pathlib import Path
import sys
import os
import json # Para imprimir diccionarios de forma legible

# --- Configuración de Path para encontrar los módulos de SAM ---
SAM_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(SAM_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(SAM_PROJECT_ROOT))

from lanzador.clients.aa_client import AutomationAnywhereClient
from lanzador.utils.config import ConfigManager, setup_logging

# --- Configurar Logging Básico para la Prueba ---
logger = setup_logging() # Usa el logger configurado por SAM
logger.setLevel(logging.INFO) # Asegurarse de que veamos los logs INFO del cliente

def get_input(prompt_message, default_value=None, data_type=str):
    """Función auxiliar para obtener entrada del usuario con un valor por defecto."""
    if default_value is not None:
        prompt_message += f" (default: {default_value})"
    
    user_input_str = input(f"{prompt_message}: ").strip()
    
    if not user_input_str and default_value is not None:
        return default_value
    if not user_input_str and data_type is not list and data_type is not dict: # Para listas y dicts, un string vacío no es None
        return None

    try:
        if data_type == bool:
            return user_input_str.lower() in ['true', 't', 'yes', 'y', '1']
        elif data_type == int:
            return int(user_input_str)
        elif data_type == list: # Espera una lista separada por comas
            return [item.strip() for item in user_input_str.split(',') if item.strip()]
        elif data_type == dict: # Espera un JSON string
            return json.loads(user_input_str) if user_input_str else {}
        return user_input_str
    except ValueError:
        logger.error(f"Entrada inválida. Se esperaba tipo {data_type}.")
        return default_value if default_value is not None else None


def pretty_print_json(data):
    """Imprime un diccionario o lista de forma legible."""
    if data is None:
        print("None")
    elif isinstance(data, (dict, list)):
        print(json.dumps(data, indent=4, ensure_ascii=False))
    else:
        print(data)

def run_manual_test():
    logger.info("--- Iniciando Prueba de Integración Manual del Cliente API SAM ---")
    print("\nEste script realizará llamadas REALES a tu Control Room A360.")
    print("Asegúrate de tener a mano la información de tu entorno de PRUEBAS/DESARROLLO.")

    # --- Obtener Configuración del Usuario ---
    print("\n--- Configuración del Cliente API ---")
    cr_url = get_input("URL del Control Room A360", "https://aaprpacrp102.tmoviles.com.ar")
    username = get_input("Usuario API de A360", "sambot")
    password = get_input("Contraseña del Usuario API", "****") # Pedir siempre, no mostrar default
    api_key = get_input("API Key (opcional, dejar vacío si no se usa)", None)
    callback_url = get_input("URL de Callback para despliegues (opcional)", "http://localhost:8000/callback")
    
    timeout = get_input("Timeout para peticiones API (segundos)", 60, int)
    buffer_token = get_input("Buffer de refresco de token (segundos)", 1140, int)
    page_size = get_input("Tamaño de página por defecto para listados", 5, int)

    if not all([cr_url, username, password is not None]): # password puede ser string vacío
        logger.error("URL, usuario y contraseña son requeridos para inicializar el cliente.")
        return

    client = AutomationAnywhereClient(
        control_room_url=cr_url,
        username=username,
        password=password,
        api_key=api_key,
        callback_url_for_deploy=callback_url,
        api_timeout_seconds=timeout,
        token_refresh_buffer_sec=buffer_token,
        default_page_size=page_size,
        logger_instance=logger
    )
    logger.info("Cliente API SAM inicializado.")

    while True:
        print("\n--- ¿Qué método quieres probar? ---")
        print("1. Desplegar Bot (desplegar_bot)")
        print("2. Obtener Detalles de Deployment(s) (obtener_detalles_por_deployment_ids)")
        print("3. Obtener Devices (Equipos) (obtener_devices_para_sam)")
        print("4. Obtener Usuarios Detallados (obtener_usuarios_detallados_para_sam)")
        print("5. Obtener Robots (obtener_robots_para_sam)")
        print("0. Salir")

        choice = get_input("Elige una opción", "0")

        try:
            if choice == '1':
                print("\n--- Prueba: desplegar_bot ---")
                file_id = get_input("File ID del bot a desplegar", None, int)
                user_ids_str = get_input("Run As User ID(s) (separados por coma si son varios)", None, str)
                run_as_user_ids = [int(uid.strip()) for uid in user_ids_str.split(',') if uid.strip()] if user_ids_str else []
                
                bot_input_str = get_input("Bot Input (JSON string, ej: {\"nombre_var\":{\"type\":\"STRING\",\"string\":\"valor\"}}, o dejar vacío)", "{}", str)
                bot_input = json.loads(bot_input_str) if bot_input_str and bot_input_str !="{}" else None

                if file_id and run_as_user_ids:
                    logger.info(f"Llamando a desplegar_bot(file_id={file_id}, run_as_user_ids={run_as_user_ids}, bot_input={bot_input})")
                    deployment_id = client.desplegar_bot(file_id, run_as_user_ids, bot_input)
                    print("Respuesta (Deployment ID):")
                    pretty_print_json(deployment_id)
                else:
                    print("File ID y Run As User ID(s) son requeridos.")

            elif choice == '2':
                print("\n--- Prueba: obtener_detalles_por_deployment_ids ---")
                dep_ids_str = get_input("Deployment ID(s) (separados por coma)", None, str)
                deployment_ids = [did.strip() for did in dep_ids_str.split(',')] if dep_ids_str else []
                if deployment_ids:
                    logger.info(f"Llamando a obtener_detalles_por_deployment_ids(deployment_ids={deployment_ids})")
                    detalles = client.obtener_detalles_por_deployment_ids(deployment_ids)
                    print("Respuesta (Detalles):")
                    pretty_print_json(detalles)
                else:
                    print("Se requiere al menos un Deployment ID.")

            elif choice == '3':
                print("\n--- Prueba: obtener_devices_para_sam ---")
                status_filter = get_input("Filtrar por status (ej. CONNECTED, DISCONNECTED, dejar vacío para todos los que permite el método)", "CONNECTED")
                logger.info(f"Llamando a obtener_devices_para_sam(status_filtro='{status_filter}')")
                devices = client.obtener_devices_para_sam(status_filter if status_filter else None)
                print(f"Respuesta ({len(devices)} Devices):")
                pretty_print_json(devices[:5]) # Mostrar solo los primeros 5 para no saturar
                if len(devices) > 5: print(f"... y {len(devices)-5} más.")


            elif choice == '4':
                print("\n--- Prueba: obtener_usuarios_detallados_para_sam ---")
                desc_filter = get_input("Filtrar por descripción de usuario que contiene (opcional)", None)
                user_ids_filter_str = get_input("Filtrar por User IDs específicos (separados por coma, opcional)", None)
                user_ids_list = [int(uid.strip()) for uid in user_ids_filter_str.split(',') if uid.strip()] if user_ids_filter_str else None
                
                logger.info(f"Llamando a obtener_usuarios_detallados_para_sam(filtro_descripcion_contiene='{desc_filter}', user_ids={user_ids_list})")
                usuarios = client.obtener_usuarios_detallados_para_sam(
                    filtro_descripcion_contiene=desc_filter,
                    user_ids=user_ids_list
                )
                print(f"Respuesta ({len(usuarios)} Usuarios):")
                pretty_print_json(usuarios[:5])
                if len(usuarios) > 5: print(f"... y {len(usuarios)-5} más.")


            elif choice == '5':
                print("\n--- Prueba: obtener_robots_para_sam ---")
                path_filter = get_input("Filtrar por path que contiene (opcional, ej. 'Bots/Finanzas')", None)
                logger.info(f"Llamando a obtener_robots_para_sam(filtro_path_contiene='{path_filter}')")
                robots = client.obtener_robots_para_sam(filtro_path_contiene=path_filter)
                print(f"Respuesta ({len(robots)} Robots):")
                pretty_print_json(robots[:5])
                if len(robots) > 5: print(f"... y {len(robots)-5} más.")

            elif choice == '0':
                logger.info("Saliendo de la prueba manual.")
                break
            else:
                print("Opción no válida.")
        
        except Exception as e:
            logger.error(f"Ocurrió un error durante la prueba del método: {e}", exc_info=True)
            print(f"ERROR: {e}")

    logger.info("--- Prueba de Integración Manual Finalizada ---")


if __name__ == "__main__":
    run_manual_test()