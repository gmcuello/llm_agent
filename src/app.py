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
LLM_HOST = cfgs.LLM_HOST
LLM_PORT = cfgs.LLM_PORT

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

def filtrar_datos_vivaldi(query_pandas: str, results_df=None) -> (str, pd.DataFrame):
    url_gateway = "http://localhost:8000/api/v1/pozos/all"
    try:
        # results_df puede traer resultados previamente filtrados por alguna iteracion del run_agent
        if results_df is None:
            df = fetch_from_api()
        else:
            df = results_df

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
        return mensaje_base + f"Datos completos:\n{df_filtrado.to_csv(index=False)}", df_filtrado
    except Exception as e:
        return f"Error al procesar el filtro en Pandas: {str(e)}", None

def ejecutar_codigo_pandas(codigo_pandas: str, results_df=None) -> (str, pd.DataFrame):
    try:
        # results_df puede traer resultados previamente filtrados por alguna iteracion del run_agent
        if results_df is None:
            df = fetch_from_api()
        else:
            df = results_df

        codigo_limpio = codigo_pandas.strip("`'\"")
        entorno_global = {"pd": pd, "np": np}
        entorno_local = {"df": df}
        resultado = eval(codigo_limpio, entorno_global, entorno_local)
        if isinstance(resultado, pd.Series) or isinstance(resultado, pd.DataFrame):
            return resultado.to_string(), resultado
        else:
            return str(resultado), resultado
    except Exception as e:
        return f"Error en la sintaxis de Pandas: {str(e)}", None


# ==========================================
# ESQUEMA Y PROMPTS PARA LOS AGENTES
# ==========================================
HERRAMIENTAS = """    
        1. filtrar_datos_vivaldi: Úsala para extraer filas usando df.query() (ej. estado == 'Falla'). El argumento solo debe ser el argumento y no el string completo ("df.query(argumento)")
        Por la descripcion del schema vas a leer Sx o Sy. En ese caso, deberas generar todas las posibilidades: SA, SB, SC para ellos. Si estan Sx y Sy juntos, A,B o C no se repiten. Indica un par de posibles SA,SB o SB, SC 
        Cuando se pregunte por cuantos pozos estan en cierto estado, debe incluirse unique() para el equip_name.
        2. ejecutar_codigo_pandas: Úsala para realizar agrupaciones (groupby), conteos avanzados, promedios, máximos, mínimos o extraer top N. 
               
        - El DataFrame se llama 'df'.
        - El argumento DEBE ser una expresión de código Python en una sola línea.
        - Ejemplo para promedio: df['presion_psi'].mean()
        - Ejemplo para conteo por grupo: df.groupby('estado').size()
        - Ejemplo para buscar el máximo: df.nlargest(5, 'temperatura')
        """

nombres_herramientas = "filtrar_datos_vivaldi, ejecutar_codigo_pandas"

SCHEMA_DATAFRAME = """
METADATOS DEL DATAFRAME df (ESQUEMA):
        - Columnas disponibles:
            * 'equip_name': nombre del equipo o pozo (ej. 'YPF.Nq.LLL-256')
            * 'analyzer_id':  nombre del analizador que generó el status.
            * 'target_server':  servidor PI AF desde donde se leen los datos.
            * 'last_updated':  timestamp de última actualización del status.
            * 'status': código del estado.
            * 'explanation': explicación que fundamenta el por qué del código de estado, basado en los analisis previos.
            * 'graph_url':  path y nombre del archivo con el grafico complementario que soporta al código de estado.
            * 'uwi':  unique well identifier del pozo.
            * 'oh_lvl_1': nivel jerarquico 1. 1 es el de mayor nivel
            * 'oh_lvl_2': nivel jerarquico 2
            * 'oh_lvl_3': nivel jerarquico 3
            * 'oh_lvl_4': nivel jerarquico 4
            * 'oh_lvl_5': nivel jerarquico 5
            * 'api_nro':  unique well identifier del pozo.
            * 'completacion_id': id de la completación del pozo.
            * 'fecha_efectiva_dt':  fecha del control del pozo.
            * 'control_petroleo_m3_val':  control del petróleo del pozo.
            * 'control_agua_m3_val': control del agua del pozo.
            * 'control_gas_m3_val':  control del gas del pozo.
            * 'tamano_orificio_val':  tamaño del orificio del pozo (aplica a metodo de producción surgente).
            * 'proposito_control_cd': código de propósito del control.
            * 'vol_potencial_petroleo_m3_num':  potencioal de petróleo del pozo.
            * 'vol_potencial_gas_m3_num': potencioal de gas del pozo.
            * 'fecha_potencial_dt':  fecha de cálculo del potencioal del pozo.
            * 'metodo_produccion_historico_cd': código del método de producción del pozo.
            * 'metodo_produccion_desc':  descripción del método de producción.
            * 'riesgo_pozo':  riesgo de integridad del pozo (ej. Riesgo 0, Riesgo 1). Riesgo 0 es el mayor riesgo.
            * 'fecha_ejecucion: timestamp del cálculo del riesgo.
        - Diccionario de Status Codes:
             <analisis> puede figurar como: INTEGRITY_DATA, INTEGRITY_SECTIONS_CONNECTED, INTEGRITY_THERMAL_EFFECT, INTEGRITY_PRESSURE_, INTEGRITY_PRESSURE_INCREMENT_DECREMENT
             <analisis>_NO_COMM`: No comunica.
            `<analisis>_NOT_POSSIBLE`: Análisis no fue posible (cuando no se dispone de ninguna señal para el análisis).
            `<analisis>_NORMAL`: Normal.
            * en cuanto a calidad de Datos:
                `<analisis>_SA_SB_SC_BAD_DATA`: Todas las señales presentan error de datos.
                `<analisis>_Sx_BAD_DATA`: los datos de la sección  x no se disponible. Sx puede ser: SA, SB o SC.
                `<analisis>_Sx_Sy_BAD_DATA`: los datos de las secciones x e y no se disponibles.  Sx puede ser: SA, SB o SC. Sy puede ser: SA, SB o SC.
            * en cuanto a Presurización, secciones presurizadas:
                `<analisis>_SA_SB_SC_PRESSURIZED`: todas las secciones están presurizadas.
                `<analisis>_Sx_Sy_PRESSURIZED`: la seccion x y la seccion y están presurizadas. Sx puede ser: SA, SB o SC. Sy puede ser: SA, SB o SC.
                `<analisis>_Sx_PRESSURIZED`: la sección x esta presurizada. Sx puede ser: SA, SB o SC.
            * en cuanto a incrementos o decrementos de presión
                `<analisis>_Sx_INCREASE`: la sección x está incrementando presión. Sx puede ser: SA, SB o SC.
                `<analisis>_Sx_Sy_INCREASE`: las secciones x e y están incrementando presión. Sx puede ser: SA, SB o SC. Sy puede ser: SA, SB o SC. 
                `<analisis>_SA_SB_SC_INCREASE`: las tres secciones están incrementando presión.
                `<analisis>_Sx_DECREASE`: la sección x está decrementando presión. Sx puede ser: SA, SB o SC.
                `<analisis>_Sx_Sy_DECREASE`: las secciones x e y están decrementando presión. Sx puede ser: SA, SB o SC. Sy puede ser: SA, SB o SC. 
                `<analisis>_SA_SB_SC_DECREASE`: las tres secciones están decrementando presión.
            * En cuanto a secciones comunicadas
                `<analisis>_SA_SB_SC_CONNECTED`: las tres secciones están comunicadas. 
                `<analisis>_Sx_Sy_CONNECTED`: la sección x está comunicada con la sección y. Sx puede ser: SA, SB o SC. Sy puede ser: SA, SB o SC. 
            * En cuanto a efecto térmico
                `<analisis>_SA_SB_SC_THERMAL_DAILY`: las tres secciones presentan efecto térmico. 
                `<analisis>_Sx_Sy_THERMAL_DAILY`: las secciones x e y presentan efecto térmico. Sx puede ser: SA, SB o SC. Sy puede ser: SA, SB o SC. 
                `<analisis>_Sx_THERMAL_DAILY`: la sección x presenta efecto térmico. Sx puede ser: SA, SB o SC."""

PROMPT_TELEMETRIA = f"""Responde a las siguientes preguntas lo mejor que puedas. Tienes acceso a las siguientes herramientas:

{HERRAMIENTAS}
El nombre de las herramientas es:
{nombres_herramientas}

y el esquema de datos del dataframe df es:

{SCHEMA_DATAFRAME}.

Para interactuar, debes usar el siguiente formato de manera estricta:

Pregunta: la pregunta de entrada que debes resolver
Pensamiento: siempre debes explicar en qué estás pensando y qué vas a hacer a continuación
Acción: la acción que vas a tomar. Debe ser excluyentemente una de la lista: [{nombres_herramientas}]
Entrada de la Acción: los parámetros o argumentos que requiere la acción
Observación: el resultado devuelto por la acción ejecutada
... (este ciclo Pensamiento/Acción/Entrada de la Acción/Observación puede repetirse N veces)
Pensamiento: ahora tengo la información suficiente para dar la respuesta
Respuesta Final: la respuesta final y consolidada a la pregunta original de entrada

¡Comienza!
"""



PROMPT_CALIDAD = f"""Responde a las siguientes preguntas lo mejor que puedas. Eres un Inspector estricto de Calidad de Datos (Data Quality).
Tu objetivo es auditar fallas de datos (BAD_DATA), telemetría congelada, falta de comunicación o nulos.

{SCHEMA_DATAFRAME}"""


# ==========================================
# EL SUPERVISOR (ENRUTADOR SEMÁNTICO)
# ==========================================
def clasificar_intencion(consulta: str) -> str:
    url = f"{LLM_HOST}:{LLM_PORT}/api/generate"
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
