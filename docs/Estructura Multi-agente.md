# Estructura Multi-agente (Multi agent system)
El estado del arte absoluto en la industria hoy se llama Arquitecturas Multi-Agente (MAS - Multi-Agent Systems), frecuentemente orquestadas mediante grafos (como LangGraph) o frameworks de agentes conversacionales (como AutoGen o CrewAI).

Lo que estás intuyendo es exactamente hacia dónde convergió la ingeniería de IA: en lugar de tener un "Agente Dios" (un mega-prompt monolítico que intenta hacer consultas SQL, análisis de calidad de datos y conversar al mismo tiempo), se divide el trabajo en especialistas coordinados.

Para el nivel de orquestación de LLMs locales que estás investigando, estructurarlo de esta manera resuelve de un plumazo la degradación de atención de la red neuronal y limita el riesgo de alucinaciones. Es, en esencia, llevar la lógica y el control de tus máquinas de estados finitos al plano semántico.

Así se diseña una topología Multi-Agente estándar para telemetría industrial:

1. El Agente Supervisor (El Enrutador Semántico)
Es un modelo muy rápido (puede ser el mismo Qwen o Gemma) con un único trabajo: entender la intención del operador y delegar la tarea. No tiene acceso a Pandas, ni a PI AF, ni a bases de datos.

Su Prompt: "Eres el supervisor de la sala de control. Analiza el pedido del usuario y decide a qué especialista llamar: [Agente_Datos, Agente_Calidad, Agente_Charlatan]".

Si el usuario dice: "Buen día, ¿hay novedades?", lo envía al Agente_Charlatan.

Si el usuario dice: "Dime la presión del pozo 4", lo deriva al Agente_Datos.

2. El Agente Especialista en Datos (Data Analyst Worker)
Este agente solo despierta cuando el supervisor se lo ordena. Su contexto está puramente enfocado en extracción de información.

Sus Herramientas: explorar_arbol_af, ejecutar_codigo_pandas, filtrar_datos_vivaldi.

Su Prompt: "Eres un analista de datos OT-IT. Tu único objetivo es extraer datos crudos, agruparlos o filtrarlos usando las herramientas provistas y devolver la respuesta limpia. No evalúes la calidad del dato, asume que es correcto."

3. El Agente de Calidad de Datos (DQ Inspector Worker)
Este es el sabueso de anomalías. Tiene una personalidad matemática estricta y herramientas dedicadas.

Sus Herramientas: analizar_congelamiento_por_template, detectar_outliers_estadisticos, verificar_nulos.

Su Prompt: "Eres un inspector de calidad de datos. Nunca confíes en los sensores. Tu trabajo es ejecutar scripts estadísticos para encontrar flatlines, lagunas temporales o valores espurios. Reporta estrictamente las anomalías."

Por qué esta arquitectura es superior
Aislamiento de Herramientas (Seguridad): El agente que audita la calidad no tiene la herramienta para inyectar queries arbitrarios, por lo que es imposible que rompa algo accidentalmente.

Economía de Tokens: En lugar de inyectar el diccionario completo de estados, el esquema del árbol de AF y las reglas de Data Quality en cada iteración de un solo agente gigante, cada especialista carga en su memoria RAM de contexto únicamente lo que necesita para su dominio.

Mantenibilidad de Código: Si el día de mañana quieres agregar un nuevo caso de uso (por ejemplo, un "Agente de Mantenimiento Predictivo" que lea órdenes de trabajo), simplemente agregas un nodo al Supervisor y escribes un script aislado, sin tocar el código de los otros agentes.