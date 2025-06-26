# src/interfaz_web/components/styles.py

# --- Estilos para Títulos ---
TITLE_STYLES = {
    "h1": "text-3xl font-bold text-gray-900 tracking-tight",
    "h2": "text-2xl font-semibold text-gray-900",
    "h3": "text-lg font-semibold text-gray-800 mb-4",
}

# --- Estilos para Formularios ---
LABEL_STYLES = {
    "default": "block text-sm font-medium text-gray-700",
}

INPUT_STYLES = {
    "default": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900 bg-white",
}

# --- Estilos para Botones (que ya tenías) ---
BUTTON_STYLES = {
    "primary": "px-4 h-10 rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 font-semibold",
    "secondary": "px-4 h-10 rounded-md bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 disabled:opacity-50 font-semibold",
    "danger": "px-4 h-10 rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 font-semibold",
    "menu_item": "block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100",
}

# --- Estilos para Párrafos y Spans (opcional) ---
TEXT_STYLES = {
    "body": "text-base text-gray-800",
    "caption": "text-sm text-gray-500",
    "error": "text-sm text-red-600",
}
