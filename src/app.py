import hashlib

import requests
import pandas as pd
import numpy as np
import re
import os

from utils.LOGGING import log  # Importar el módulo de logging
from utils.CONFIGS import app_config as cfgs  # Importar cfgs para el nombre del log
# utils URL de tu nueva API (asegúrate de que coincida con el puerto donde corre el .exe de la API)
API_DIAGNOSTICS_URL = cfgs.API_DIAGNOSTICS_URL #  "http://127.0.0.1:5052/api/v1/diagnosticos"  #

# Obtener una instancia del logger para este módulo
logger = log.getLogger(log.NAME_LOG)


# Puedes mover este flag y la ruta a tu archivo utils/CONFIGS.py
DEVELOP_MODE = False
MOCK_FILE = "diagnosticos_mock.pkl"

def fetch_from_api(develop: bool = DEVELOP_MODE) -> pd.DataFrame:
    """
    Solicita los datos a la API, ofusca nombres sensibles en desarrollo,
    o lee el DataFrame serializado si develop=True.
    """
    # 1. Modo Desarrollo: Intentar leer el binario local (que ya estará ofuscado)
    if develop and os.path.exists(MOCK_FILE):
        logger.info(f"[DEVELOP] Leyendo DataFrame ofuscado desde {MOCK_FILE}")
        return pd.read_pickle(MOCK_FILE)

    # 2. Lógica real de la API
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

        # ==========================================
        # CAPA DE CIBERSEGURIDAD: OFUSCACIÓN DE DATOS
        # ==========================================
        if develop and 'equip_name' in df.columns:
            def ofuscar_nombre(nombre):
                if pd.isna(nombre):
                    return nombre
                # Crea un hash MD5 determinista y toma los primeros 5 caracteres
                hash_corto = hashlib.md5(str(nombre).encode('utf-8')).hexdigest()[:5].upper()
                return f"MOCK.PZ-{hash_corto}"

            # Aplicamos la ofuscación a toda las columnas sensibles
            df['equip_name'] = df['equip_name'].apply(ofuscar_nombre)
            df['target_server'] = df['target_server'].apply(ofuscar_nombre)
            df['graph_url'] = df['graph_url'].apply(ofuscar_nombre)
            logger.info("[DEVELOP] Nombres de equipos ofuscados por seguridad.")

        # 3. Guardar el archivo para la próxima ejecución offline
        if develop:
            df.to_pickle(MOCK_FILE)
            logger.info(f"[DEVELOP] DataFrame serializado y guardado en {MOCK_FILE}")

        return df

    except Exception as e:
        logger.error(f"Error en fetch_from_api: {e}")
        return pd.DataFrame()

def filtrar_datos_vivaldi(query_pandas: str) -> str:
    """
    1. Descarga el bulk de datos del API.
    2. Lo carga en Pandas localmente.
    3. Aplica la lógica de filtrado que el LLM decidió.
    4. Devuelve solo el subconjunto al LLM.
    """
    url_gateway = "http://localhost:8000/api/v1/pozos/all"

    try:
        # 1. Se carga en memoria RAM tradicional
        df = fetch_from_api()

        # Permitimos que el modelo pida "todo" si necesita contar el total absoluto
        if query_pandas.strip().lower() in ["", "all", "todo"]:
            df_filtrado = df
        else:
            df_filtrado = df.query(query_pandas)

        cantidad = len(df_filtrado)

        if cantidad == 0:
            return "Se encontraron exactamente 0 registros."

        # CRÍTICO: El motor Python hace la matemática y se la entrega al LLM
        mensaje_base = f"Se encontraron exactamente {cantidad} equipos que cumplen la condición.\n"

        if cantidad > 20:
            resumen = df_filtrado.head(20).to_csv(index=False)
            return mensaje_base + f"Muestra de 20 resultados:\n{resumen}"

        return mensaje_base + f"Datos completos:\n{df_filtrado.to_csv(index=False)}"

    except Exception as e:
        return f"Error al procesar el filtro en Pandas: {str(e)}"

# ==========================================
# 1. CLIENTE DEL LLM (OLLAMA LOCAL)
# ==========================================
def llamar_llm(prompt_completo: str, modelo: str = "gemma4") -> str:
    """
    Envía el prompt al modelo local.
    CRÍTICO: El parámetro 'stop' es lo que obliga al modelo a devolverle el
    control a Python para que ejecute la herramienta.
    """
    url = "http://10.111.13.28:11434/api/generate"
    payload = {
        "model": modelo,
        "prompt": prompt_completo,
        "stream": False,
        # CRÍTICO: Ollama requiere que 'stop' esté dentro de 'options'
        "options": {
            "stop": ["Observación:", "Observacion:", "Observación:\n"]
        }
    }

    try:
        respuesta = requests.post(url, json=payload, timeout=420)
        respuesta.raise_for_status()
        return respuesta.json().get("response", "")
    except Exception as e:
        return f"Error conectando con Ollama: {str(e)}"

# ==========================================
# 2. EL ORQUESTADOR REACT (BUCLE WHILE)
# ==========================================
def ejecutar_agente_scada(pregunta_usuario: str, max_iteraciones: int = 5):
    # 1. Definimos las herramientas disponibles usando el formato exacto de LangChain
    herramientas_desc = """
        METADATOS DEL DATAFRAME df (ESQUEMA):
        - Columnas disponibles:
            * 'equip_name': nombre del equipo o pozo (ej. 'YPF.Nq.LLL-256')
            * 'analyzer_id':  nombre del analizador que generó el status.
            * 'target_server':  servidor PI AF desde donde se leen los datos.
            * 'last_updated':  timestamp de última actialización del status.
            * 'status': código del estado.
            * 'explanation': explicación que fundamenta el por qué del código de estado, basado en los analisis previos.
            * 'graph_url':  path y nombre del archivo con el grafico complementario que soporta al código de estado.
            * 'uwi':  unique well identifier del pozo.
            * 'oh_lvl_1':  
            * 'oh_lvl_2':  
            * 'oh_lvl_3': 
            * 'oh_lvl_4':  
            * 'oh_lvl_5':  
            * 'api_nro':  
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
            `FSM_NO_COMM`: No comunica.
            `FSM_NOT_POSSIBLE`: Análisis no fue posible (cuando no se dispone de ninguna señal para el análisis).
            * en cuanto a calidad de Datos:
                `FSM_SA_SB_SC_BAD_DATA`: Todas las señales presentan error de datos.
                `FSM_Sx_BAD_DATA`: los datos de la sección  x no se disponible. x puede ser: A, B o C.
                `FSM_Sx_Sy_BAD_DATA`: los datos de las secciones x e y no se disponibles.  x puede ser: A, B o C. y puede ser: A, B o C.
            * en cuanto a Presurización, secciones presurizadas:
                `FSM_SA_SB_SC_PRESSURIZED`: todas las secciones están presurizadas.
                `FSM_Sx_Sy_PRESSURIZED`: la seccion x y la seccion y están presurizadas. x puede ser: A, B o C. y puede ser: A, B o C.
                `FSM_Sx_PRESSURIZED`: la sección x esta presurizada. x puede ser: A, B o C.
            * en cuanto a incrementos o decrementos de presión
                `FSM_Sx_INCREASE`: la sección x está incrementando presión. x puede ser: A, B o C.
                `FSM_Sx_Sy_INCREASE`: las secciones x e y están incrementando presión. x puede ser: A, B o C. y puede ser: A, B o C. 
                `FSM_SA_SB_SC_INCREASE`: las tres secciones están incrementando presión.
                `FSM_Sx_DECREASE`: la sección x está decrementando presión. x puede ser: A, B o C.
                `FSM_Sx_Sy_DECREASE`: las secciones x e y están decrementando presión. x puede ser: A, B o C. y puede ser: A, B o C. 
                `FSM_SA_SB_SC_DECREASE`: las tres secciones están decrementando presión.
            * En cuanto a secciones comunicadas
                `FSM_SA_SB_SC_CONNECTED`: las tres secciones están comunicadas. 
                `FSM_Sx_Sy_CONNECTED`: la sección x está comunicada con la sección y. x puede ser: A, B o C. y puede ser: A, B o C. 
            * En cuanto a efecto térmico
                `FSM_SA_SB_SC_THERMAL_DAILY`: las tres secciones presentan efecto térmico. 
                `FSM_Sx_Sy_THERMAL_DAILY`: las secciones x e y presentan efecto térmico. x puede ser: A, B o C. y puede ser: A, B o C. 
                `FSM_Sx_THERMAL_DAILY`: la sección x presenta efecto térmico. x puede ser: A, B o C.
    
        1. filtrar_datos_vivaldi: Úsala para extraer filas usando df.query() (ej. estado == 'Falla').

        2. ejecutar_codigo_pandas: Úsala para realizar agrupaciones (groupby), conteos avanzados, promedios, máximos, mínimos o extraer top N. 
               
        - El DataFrame se llama 'df'.
        - El argumento DEBE ser una expresión de código Python en una sola línea.
        - Ejemplo para promedio: df['presion_psi'].mean()
        - Ejemplo para conteo por grupo: df.groupby('estado').size()
        - Ejemplo para buscar el máximo: df.nlargest(5, 'temperatura')
        """
    nombres_herramientas = "filtrar_datos_vivaldi, ejecutar_codigo_pandas"

    # 2. El Prompt ReAct clásico que mencionaste
    prompt_base = f"""Responde a las siguientes preguntas lo mejor que puedas. Tienes acceso a las siguientes herramientas:

{herramientas_desc}

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

Pregunta: {pregunta_usuario}
Pensamiento: """

    historial = prompt_base

    print(f"\n[INICIO] Procesando solicitud: '{pregunta_usuario}'\n")

    for i in range(max_iteraciones):
        print(f"--- Iteración {i + 1} ---")

        # Llamada a Ollama
        texto_generado = llamar_llm(historial)

        # 2. BARRERA DEFENSIVA: Si el modelo logró alucinar la observación, la borramos.
        if "Observación:" in texto_generado:
            texto_generado = texto_generado.split("Observación:")[0]

        # Imprimimos lo que el modelo generó para depurar
        print(f"\n[Salida del LLM]:\n{texto_generado}\n")

        historial += texto_generado

        if "Respuesta Final:" in texto_generado:
            respuesta_final = texto_generado.split("Respuesta Final:")[-1].strip()
            print("\n[ÉXITO] Lazo terminado.")
            return respuesta_final

        patron = r"Acción:\s*(.*?)\nEntrada de la Acción:\s*(.*)"
        match = re.search(patron, texto_generado)

        if match:
            herramienta = match.group(1).strip()
            argumento = match.group(2).strip()

            print(f"  [Parseo] Ejecutando: {herramienta}({argumento})")

            if herramienta == "filtrar_datos_vivaldi":
                resultado_real = filtrar_datos_vivaldi(argumento)
            elif herramienta == "ejecutar_codigo_pandas":
                print("  [Sistema] Ejecutando operación nativa de Pandas...")
                resultado_real = ejecutar_codigo_pandas(argumento)
            else:
                resultado_real = f"Error: La herramienta {herramienta} no existe."

            observacion = f"\nObservación: {resultado_real}\nPensamiento: "
            historial += observacion

        else:
            # CRÍTICO: Si el modelo intentó responder sin usar la acción, lo penalizamos.
            print("  [Error] El modelo no generó una Acción válida. Forzando corrección.")
            historial += "\nObservación: Error de formato. Debes usar una herramienta con 'Acción:' y 'Entrada de la Acción:' antes de dar la Respuesta Final.\nPensamiento: "

    return "No pude resolver la consulta."

def ejecutar_codigo_pandas(codigo_pandas: str) -> str:
    """
    Permite al LLM ejecutar operaciones complejas de Pandas directamente sobre el df.
    """
    try:
        # 1. Obtenemos el DataFrame actualizado de Vivaldi
        df = fetch_from_api()

        # 2. Sanitizamos un poco la entrada por si el LLM pone comillas extra
        codigo_limpio = codigo_pandas.strip("`'\"")

        # 3. Entorno de ejecución restringido (sandbox)
        entorno_global = {"pd": pd, "np": np}
        entorno_local = {"df": df}

        # 4. Ejecutamos la expresión (Ej: df.groupby('estado').size())
        resultado = eval(codigo_limpio, entorno_global, entorno_local)

        # 5. Formateamos el resultado para devolvérselo al LLM
        if isinstance(resultado, pd.Series) or isinstance(resultado, pd.DataFrame):
            return resultado.to_string()
        else:
            return str(resultado)

    except Exception as e:
        return f"Error en la sintaxis de Pandas: {str(e)}"

# ==========================================
# PUNTO DE ENTRADA
# ==========================================
if __name__ == "__main__":
    # Prueba del lazo integrado
    consulta = "¿Qué diagnósticos o estados reporta el pozo PBE.Nq.RN-1049?"
    respuesta_operador = ejecutar_agente_scada(consulta)

    print("\n==================================")
    print("RESPUESTA AL OPERADOR:")
    print("==================================")
    print(respuesta_operador)