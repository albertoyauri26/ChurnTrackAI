# Evidencias verificables

Todas las pruebas usan datos sintéticos y no acreditan efectividad comercial en una empresa. Las fechas corresponden a la ejecución real. Los archivos de `evidence/` se generaron con la aplicación y no se editaron a mano.

## Casos de prueba

| ID | Caso | Entrada | Resultado esperado | Resultado obtenido | Agentes | Estado | Evidencia |
|---|---|---|---|---|---|---|---|
| CP01 | Flujo multiagente con Groq real, lote | CSV de 300 clientes, LLM con consentimiento | Tres etapas validadas para 20 clientes; el resto con reglas | Predictivo 1.641 ms, Retención 837 ms, Supervisor 995 ms, todas `validated`; 12 mensajes; 4.686 ms en total (23/10/2026) | Supervisor, Predictivo, Retención + Groq | Aprobado | `evidence/redesign-verification.json` |
| CP02 | Flujo con Groq real, un cliente | Cliente B2B-001 en https://churntrackai-4omr.onrender.com | 1/1 con LLM en las tres etapas | Las tres etapas `validated` con tu clave Groq: 1.601 tokens de entrada y 275 de salida; 12 mensajes; 1.271 ms (24/10/2026). En el navegador, diagnóstico con 1/1 acciones del LLM, una propuesta pendiente de aceptación y consola sin errores | Los tres + Groq | Aprobado | `evidence/live-stream-public.json`; antes, `evidence/three-agent-live.json` (despliegue original, 22/10/2026) |
| CP03 | Límite de la API de Groq | Lote de 300 tras ejecuciones seguidas | Se informa la cuota, sin reintento ni respuesta inventada | Retención y Supervisor reciben `HTTP_429_PROVIDER_REJECTED`; las recomendaciones salen por reglas, con aviso visible | Retención, Supervisor | Aprobado | `evidence/three-agent-batch-quota.json` |
| CP04 | Salida LLM no fundamentada | Respuesta del Predictivo con acción fuera de su esquema | Se rechaza esa etapa sin afectar las demás | Predictivo `UNSUPPORTED_RECOMMENDATION`; Retención y Supervisor validados. Se corrigió restringiendo el esquema por etapa (commit 27d6116) | Predictivo, Supervisor | Aprobado tras corrección | `evidence/three-agent-rejected-before-fix.json` |
| CP05 | Entradas inválidas | 301 filas, columnas erróneas, duplicados, negativos, NaN | HTTP 422 antes de la inferencia | 422 en todos los casos; la vista previa no ejecuta el modelo | API, Predictivo | Aprobado | `tests/test_public_workflow.py`, `tests/test_system.py`, `tests/test_intake.py` |
| CP06 | Modelo predictivo | 204 entradas de paridad; 1.000 sintéticos nuevos | Paridad con `modelo.js`; métricas superiores a la línea base | Error máximo 5,55e-17. Accuracy 0,927 frente a 0,678 de la línea base «todo churn»; F1 0,946; AUC 0,981; Brier 0,053 | Predictivo | Aprobado (solo dominio sintético) | `models/evaluation.json` |
| CP07 | Estado de agentes en vivo | `POST /api/public/analyze?stream=true` en producción con Groq | Cada mensaje llega cuando el agente lo registra, antes del informe | Producción: mensajes 1–4 a 0,39 s; 5–7 a 0,83 s; 8–10 a 1,15 s; 11–12 a 1,51 s, en paralelo a cada llamada a Groq. Local, con un proveedor simulado de 1 s: escalones a 1,1 / 2,1 / 3,2 / 4,2 s. La interfaz mostró «Ejecutando» y «Completado» por agente | Los tres + Groq | Aprobado | `evidence/live-stream-public.json`, `tests/test_public_workflow.py::test_stream_emits_each_trace_message_before_the_run`, `evidence/live-agents-local.jpg` |
| CP08 | Respuesta malformada o vacía del proveedor | HTTP 200 con cuerpo nulo; JSON fuera de esquema | Error controlado, sin exponer el cuerpo, uso de reglas | `ProviderError`, mensaje comprensible, sin secretos | Retención | Aprobado (doble HTTP) | `tests/test_llm_compact.py`, `tests/test_public_workflow.py` |
| CP09 | Control de acceso | Endpoints privados sin clave | 401; el análisis público no persiste | 401 en análisis privado, historial y decisiones; los análisis públicos no aparecen en el historial | API | Aprobado | `tests/test_public_workflow.py::test_public_boundary_and_private_isolation` |
| CP10 | Interfaz sin errores | Carga y análisis en el navegador | Consola sin errores | Antes: `pattern` inválido en el código de cliente, que desactivaba la validación del navegador. Tras corregirlo, la consola quedó limpia (24/10/2026, local) | Frontend | Aprobado en local | `frontend/index.html` |
| CP11 | Concurrencia pública | 6 `POST /api/demo?size=300` simultáneos | Todos atendidos sin errores | 6 × HTTP 200; mediana y máximo de 10,4 s. La inferencia se procesa en serie en un worker: unos 1,7 s por lote de 300 (24/10/2026) | Los tres, sin LLM | Aprobado con observación | `evidence/http-measurements-public.json` |
| CP12 | Latencia pública | 5 muestras por endpoint | Respuesta en menos de 1 s con el servicio despierto | Mediana: `/health` 188 ms, `/` 189 ms, `/api/demo` (12 clientes) 198 ms (24/10/2026). Primera visita tras la suspensión: 21,4 s (despliegue original) | API | Aprobado | `evidence/http-measurements-public.json` |

Suite automatizada (24/10/2026, Python 3.13.17): 64 pruebas `pytest` aprobadas (`evidence/tests.xml`), 8 comprobaciones de `tests/actions.cjs` y 5 de `tests/clarity.cjs`.

Fallos encontrados en esta auditoría y su corrección: `pattern` HTML inválido (corregido), estado de agentes no observable durante la ejecución (SSE añadido), Gemini como proveedor por defecto pese a usar Groq (Groq por defecto en código, `.env.example` y `render.yaml`), texto de Configuración que pedía «activar Groq» ya activo (actualizado), sin registro de fallos del proveedor en el log del servidor (añadido) y documentación con conteos y proveedor desactualizados (actualizada).

## Matriz para el cuestionario (A–K)

«Pendiente» significa que el dato no existe en el repositorio y debe aportarlo el equipo; no se rellena con supuestos.

| Sección | Evidencia disponible | Pendiente |
|---|---|---|
| A. Datos del proyecto | Producto ChurnTrackAI. URL https://churntrackai-4omr.onrender.com (live el 24/10/2026, commit a9c9345). Repositorio público https://github.com/albertoyauri26/ChurnTrackAI. Despliegue y repositorio originales: https://churntrackai.onrender.com y https://github.com/ManuelCarranzaAv/ChurnTrackAI | Integrantes, roles y video demostrativo |
| B. Problema, usuario e innovación | Problema y usuario: `docs/USO_EMPRESARIAL.md`. Comparación con Gainsight, ChurnZero y Totango, con enlaces: `docs/REQUISITOS.md`. Evidencia del problema: Gallo, HBR, 29/10/2014: captar un cliente cuesta de 5 a 25 veces más que retenerlo, y según Reichheld (Bain), +5 % de retención eleva las utilidades entre 25 % y 95 % ([enlace](https://hbr.org/2014/10/the-value-of-keeping-the-right-customers)). Tecnología emergente: agentes coordinados con LLM por API y salida estructurada sobre una red neuronal. Medición: CP01–CP12 | Redacción final del objetivo general y de hasta tres objetivos específicos. Propuesta coherente con lo implementado: estimar el riesgo con la red neuronal; proponer acciones trazables con tres agentes; mantener la decisión humana con evidencia exportable |
| C. Requerimientos funcionales | 16 RF con código, prioridad, agente, criterio y estado; actores, flujo y exclusiones: `docs/REQUISITOS.md` | — |
| D. Requerimientos técnicos | Versiones fijadas en `requirements.txt` (FastAPI 0.156.4, Uvicorn 0.54.0, Pydantic 2.14.1, httpx 0.28.1, SQLAlchemy 2.1.5, psycopg 3.3.6, python-dotenv 1.2.4) y Python 3.13 (`Dockerfile`). Rendimiento: CP11–CP12. Disponibilidad: `/health`, sin SLA. Seguridad y privacidad: `docs/ARQUITECTURA.md`. Datos sintéticos: `docs/AUDITORIA.md`. Diagrama: `docs/ARQUITECTURA.md` | Licencia del proyecto (no hay archivo LICENSE). Copias de respaldo: no existen; SQLite en Render Free es efímero |
| E. Arquitectura multiagente | Roles, herramientas, entradas, salidas, delegación, límites, errores, intervención humana, qué se pierde sin cada agente y por qué no es un solo prompt: `docs/ARQUITECTURA.md`. Orquestación propia en Python con FastAPI y Pydantic 2.14.1, sin framework de agentes. Estado compartido por ejecución (`SharedState`), sin memoria a largo plazo. Trazas reales: `evidence/three-agent-live.json`, `evidence/redesign-verification.json` | — |
| F. Modelos, datos y costos | Groq `openai/gpt-oss-20b` para las tres etapas y red neuronal propia para el riesgo. Sin RAG ni fuentes documentales. Costo por 100 consultas con tokens medidos: `docs/DESPLIEGUE.md` | Justificación final del equipo para elegir el modelo |
| G. Despliegue | HTTPS público verificado; `Dockerfile`, `compose.yaml`, `.env.example`, `render.yaml`, README; `/health`; datos de prueba `data/template.csv` y `data/example-300.csv`; latencia y concurrencia medidas (CP11–CP12) | `docker compose` no se ejecutó localmente (Docker no está instalado); Render construye el contenedor. Prueba desde otro dispositivo |
| H. Seguridad y ética | Claves solo en el servidor; validación estricta; 401 en rutas privadas; datos tratados como evidencia y esquemas cerrados frente a prompt injection; sin códigos de cliente al LLM; acciones de un catálogo con evidencia citada; trazas; avisos de que se trata de estimaciones sin causalidad; sin acciones automáticas | Evaluación de sesgo con datos reales (no aplicable con datos sintéticos) |
| I. Pruebas y evidencias | Matriz CP01–CP12 y suite automatizada | — |
| J. Gestión del proyecto | Hitos verificables en `git log` (21/10–24/10/2026). Los 19 commits figuran con el autor de GitHub ManuelCarranzaAv | Metodología y contribución individual de cada integrante |
| K. Declaración final | Publicado y funcionando (CP02, CP12); sin claves ni datos personales en el repositorio (revisión de patrones de clave en archivos e historial, 24/10/2026); colaboración real y explicable (CP01, CP04, CP07) | Firma o confirmación del equipo |

## Otras evidencias

| Verificación | Evidencia | Resultado |
|---|---|---|
| Traza local de la demo | `evidence/demo-trace-local.json` | Tres agentes en modo reglas |
| Traza pública de la demo | `evidence/demo-trace-public.json` | 12 clientes, 6 mensajes, sin LLM (24/10/2026, servicio nuevo) |
| HTTP local | `evidence/http-measurements.json` | Cinco muestras por endpoint; no mide Internet |
| Gemini | `evidence/gemini-probe.json` | Sin generación exitosa acreditada |

Limitaciones: no hay validación empresarial; SQLite en Render Free es efímero; las aprobaciones no ejecutan acciones externas.
