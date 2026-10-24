import hashlib
import requests
import pandas as pd
import numpy as np
import re
import os

from utils.LOGGING import log
from utils.CONFIGS import app_config as cfgs
from base.BaseAgent import BaseAgent

API_DIAGNOSTICS_URL = cfgs.API_DIAGNOSTICS_URL

logger = log.getLogger(log.NAME_LOG)

DEVELOP_MODE = True
MOCK_FILE = "diagnosticos_mock.pkl"


def fetch_from_api(develop: bool = DEVELOP_MODE) -> pd.DataFrame:
    if develop and os.path.exists(MOCK_FILE):
        logger.info(f"[DEVELOP] Leyendo DataFrame ofuscado desde {MOCK_FILE}")
        return pd.read_pickle(MOCK_FILE)

    try:
        url = f"{cfgs.API_SERVER}:{cfgs.API_PORT}{cfgs.API_PREFIX}/diagnosticos?domain=integrity"
        logger.info(f"DEBUG URL: >{url}<")

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        diagnostics_list = data.get("diagnostics", [])

        if not diagnostics_list:
            logger.warning("La API respondió, pero la lista de diagnósticos está vacía.")
            return pd.DataFrame()

        df = pd.DataFrame(diagnostics_list)

        if develop and ('equip_name' in df.columns or 'target_server' in df.columns) or 'graph_url' in df.columns:
            def ofuscar_nombre(nombre):
                if pd.isna(nombre): return nombre
                hash_corto = hashlib.md5(str(nombre).encode('utf-8')).hexdigest()[:5].upper()
                return f"MOCK.PZ-{hash_corto}"

            def ofuscar_server(nombre):
                if pd.isna(nombre): return nombre
                hash_corto = hashlib.md5(str(nombre).encode('utf-8')).hexdigest()[:5].upper()
                return f"MOCK.SRVR-{hash_corto}"

            def ofuscar_oh_lvl(nombre):
                if pd.isna(nombre): return nombre
                hash_corto = hashlib.md5(str(nombre).encode('utf-8')).hexdigest()[:5].upper()
                return f"MOCK.OH_LVL-{hash_corto}"

            def ofuscar_well_id(nombre):
                if pd.isna(nombre): return nombre
                hash_corto = hashlib.md5(str(nombre).encode('utf-8')).hexdigest()[:5].upper()
                return f"MOCK.EQ_ID-{hash_corto}"

            df['equip_name'] = df['equip_name'].apply(ofuscar_nombre)
            df['target_server'] = df['target_server'].apply(ofuscar_server)  # FIX: Se quitaron los ()
            df['graph_url'] = df['graph_url'].apply(ofuscar_nombre)
            df['uwi'] = df['uwi'].apply(ofuscar_well_id)
            df['oh_lvl_1'] = df['oh_lvl_1'].apply(ofuscar_oh_lvl)
            df['oh_lvl_2'] = df['oh_lvl_2'].apply(ofuscar_oh_lvl)
            df['oh_lvl_3'] = df['oh_lvl_3'].apply(ofuscar_oh_lvl)
            df['oh_lvl_4'] = df['oh_lvl_4'].apply(ofuscar_oh_lvl)
            df['oh_lvl_5'] = df['oh_lvl_5'].apply(ofuscar_oh_lvl)
            df['api_nro'] = df['api_nro'].apply(ofuscar_well_id)  # FIX: Se quitaron los ()
            df['completacion_id'] = df['completacion_id'].apply(ofuscar_well_id)
            logger.info("[DEVELOP] Nombres de equipos ofuscados por seguridad.")

        if develop:
            df.to_pickle(MOCK_FILE)
            logger.info(f"[DEVELOP] DataFrame serializado y guardado en {MOCK_FILE}")

        return df

    except Exception as e:
        logger.error(f"Error en fetch_from_api: {e}")
        return pd.DataFrame()

def filtrar_datos_vivaldi(query_pandas: str) -> str:
    url_gateway = "http://localhost:8000/api/v1/pozos/all"
    try:
        df = fetch_from_api()
        if query_pandas.strip().lower() in ["", "all", "todo", "1 == 1", "true"]:
            df_filtrado = df
        else:
            df_filtrado = df.query(query_pandas)

        cantidad = len(df_filtrado)
        if cantidad == 0:
            return "Se encontraron exactamente 0 registros."

        mensaje_base = f"Se encontraron exactamente {cantidad} equipos que cumplen la condición.\n"
        if cantidad > 20:
            resumen = df_filtrado.head(20).to_csv(index=False)
            return mensaje_base + f"Muestra de 20 resultados:\n{resumen}"
        return mensaje_base + f"Datos completos:\n{df_filtrado.to_csv(index=False)}"
    except Exception as e:
        return f"Error al procesar el filtro en Pandas: {str(e)}"

def ejecutar_codigo_pandas(codigo_pandas: str) -> str:
    try:
        df = fetch_from_api()
        codigo_limpio = codigo_pandas.strip("`'\"")
        entorno_global = {"pd": pd, "np": np}
        entorno_local = {"df": df}
        resultado = eval(codigo_limpio, entorno_global, entorno_local)
        if isinstance(resultado, pd.Series) or isinstance(resultado, pd.DataFrame):
            return resultado.to_string()
        else:
            return str(resultado)
    except Exception as e:
        return f"Error en la sintaxis de Pandas: {str(e)}"


# ==========================================
# ESQUEMA Y PROMPTS PARA LOS AGENTES
# ==========================================
SCHEMA_DATAFRAME = """
METADATOS DEL DATAFRAME df (ESQUEMA):
- Columnas disponibles:
    * 'equip_name', 'analyzer_id', 'target_server', 'last_updated', 'status', 'explanation', 'graph_url', 'uwi', 'oh_lvl_1', 'oh_lvl_2', 'oh_lvl_3', 'oh_lvl_4', 'oh_lvl_5', 'api_nro', 'completacion_id', 'fecha_efectiva_dt', 'control_petroleo_m3_val', 'control_agua_m3_val', 'control_gas_m3_val', 'tamano_orificio_val', 'proposito_control_cd', 'vol_potencial_petroleo_m3_num', 'vol_potencial_gas_m3_num', 'fecha_potencial_dt', 'metodo_produccion_historico_cd', 'metodo_produccion_desc', 'riesgo_pozo', 'fecha_ejecucion'
- Diccionario de Status Codes:
    `FSM_NO_COMM`: No comunica.
    `FSM_NOT_POSSIBLE`: Análisis no fue posible.
    * Calidad de Datos: `FSM_SA_SB_SC_BAD_DATA`, `FSM_Sx_BAD_DATA`, `FSM_Sx_Sy_BAD_DATA`.
    * Presurización: `FSM_SA_SB_SC_PRESSURIZED`, `FSM_Sx_Sy_PRESSURIZED`, `FSM_Sx_PRESSURIZED`.
    * Incrementos/Decrementos de presión: `FSM_Sx_INCREASE`, `FSM_SA_SB_SC_INCREASE`, `FSM_Sx_DECREASE`, etc.
    * Secciones comunicadas: `FSM_SA_SB_SC_CONNECTED`, `FSM_Sx_Sy_CONNECTED`.
    * Efecto térmico: `FSM_SA_SB_SC_THERMAL_DAILY`, `FSM_Sx_Sy_THERMAL_DAILY`, `FSM_Sx_THERMAL_DAILY`.

Herramientas disponibles y REGLAS:
1. filtrar_datos_vivaldi: Úsala para extraer filas usando df.query().
2. ejecutar_codigo_pandas: Úsala para realizar agrupaciones (groupby), conteos avanzados, promedios o máximos. El argumento DEBE ser código Python en una sola línea (ej. df.groupby('status').size()).
"""

PROMPT_TELEMETRIA = f"""Responde a las siguientes preguntas lo mejor que puedas. Eres un Analista de Datos experto en telemetría SCADA.
Tu objetivo es consultar presiones, estados operativos, o agrupar información de pozos.

{SCHEMA_DATAFRAME}"""

PROMPT_CALIDAD = f"""Responde a las siguientes preguntas lo mejor que puedas. Eres un Inspector estricto de Calidad de Datos (Data Quality).
Tu objetivo es auditar fallas de datos (BAD_DATA), telemetría congelada, falta de comunicación o nulos.

{SCHEMA_DATAFRAME}"""


# ==========================================
# EL SUPERVISOR (ENRUTADOR SEMÁNTICO)
# ==========================================
def clasificar_intencion(consulta: str) -> str:
    url = "http://10.111.13.28:11434/api/generate"
    prompt_supervisor = f"""Eres el supervisor de la sala de control Vivaldi. Analiza la consulta y clasifícala.
Responde ÚNICAMENTE con una de estas dos palabras:
- 'CALIDAD': si la consulta trata sobre fallas de datos, BAD_DATA, errores, nulos o falta de comunicación.
- 'TELEMETRIA': si la consulta pide contar pozos, agrupar por niveles (oh_lvl), ver estados de presión, temperaturas o información general.

Consulta: "{consulta}"
Clasificación:"""

    payload = {
        "model": "gemma4",
        "prompt": prompt_supervisor,
        "stream": False,
        "options": {"temperature": 0.0}
    }

    try:
        respuesta = requests.post(url, json=payload, timeout=30)
        respuesta.raise_for_status()
        resultado = respuesta.json().get("response", "").strip().upper()
        if "CALIDAD" in resultado:
            return "CALIDAD"
        return "TELEMETRIA"
    except Exception as e:
        logger.error(f"[Supervisor] Error al clasificar: {e}. Default a TELEMETRIA.")
        return "TELEMETRIA"


# ==========================================
# PUNTO DE ENTRADA
# ==========================================
if __name__ == "__main__":
    # 1. Definir el diccionario de herramientas para inyectar en los agentes
    herramientas_compartidas = {
        "filtrar_datos_vivaldi": filtrar_datos_vivaldi,
        "ejecutar_codigo_pandas": ejecutar_codigo_pandas
    }

    # 2. Instanciar los agentes
    agente_telemetria = BaseAgent(
        nombre="Analista_Telemetria",
        modelo="gemma4",
        system_prompt=PROMPT_TELEMETRIA,
        herramientas=herramientas_compartidas
    )

    agente_calidad = BaseAgent(
        nombre="Inspector_DQ",
        modelo="gemma4",
        system_prompt=PROMPT_CALIDAD,
        herramientas=herramientas_compartidas
    )

    # 3. Lógica de Enrutamiento y Ejecución
    consulta = "Cuantos pozos estan incrementando presion?."

    print(f"\n[Supervisor] Analizando consulta: '{consulta}'")
    ruta = clasificar_intencion(consulta)
    print(f"[Supervisor] Decisión de enrutamiento: {ruta}")

    if ruta == "CALIDAD":
        respuesta_operador = agente_calidad.ejecutar(consulta)
    else:
        respuesta_operador = agente_telemetria.ejecutar(consulta)

    print("\n==================================")
    print("RESPUESTA AL OPERADOR:")
    print("==================================")
    print(respuesta_operador)
