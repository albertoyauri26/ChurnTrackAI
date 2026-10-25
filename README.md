# ChurnTrackAI

Plataforma académica de analítica predictiva B2B con red neuronal real y tres agentes coordinados: predictivo, retención y supervisor. Reutiliza los pesos de `modelo.js`, añade API Python, persistencia, dashboard y revisión humana.

**Estado:** aplicación publicada en https://churntrackai.onrender.com/. Flujo Inicio → Diagnóstico → Recomendaciones → Aceptación. Análisis individual y CSV hasta 300 clientes; Groq configurado en servidor. Tres roles consultan al LLM para hasta 20 clientes priorizados. Modelo académico sintético, no validado con empresas.

## Inicio rápido

Python 3.13. Desde la raíz del proyecto en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts/setup_local.py
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Abrir [la aplicación local](http://127.0.0.1:8000). `scripts/start.ps1` también inicia el servidor. Si `.venv` se creó en otra máquina (su `pyvenv.cfg` apunta a un Python inexistente), borrarla y volver a crearla con el Python 3.13 local.

1. En **Inicio**, elegir **Un cliente** o **Cartera de clientes**, ingresar indicadores y pulsar **Analizar churn**. No se solicita clave de acceso para este análisis temporal. Mientras se ejecuta, el panel muestra el estado real de Supervisor, Predictivo y Retención (pendiente, ejecutando, completado o error) con los mensajes que emite el servidor.
2. Revisar resultados y factores en **Diagnóstico**.
3. En **Recomendaciones**, seleccionar cliente y agente: Predictivo interpreta evidencia; Retención propone una acción; Supervisor revisa la propuesta. Cada etapa indica si realmente respondió el LLM o si se usaron reglas. Descargar informe y traza JSON.
4. En **Aceptación**, aceptar/rechazar individualmente o aceptar pendientes elegibles. Las propuestas marcadas para revisión adicional quedan fuera de la aceptación masiva. No se envían correos ni se modifica CRM.
5. Exportar resultados antes de cerrar. **Opciones de guardado** permite historial privado con APP_API_KEY; la consulta pública al LLM no requiere esa clave.
6. **Evaluación e historial** conserva métricas y consulta privada.

## Proveedor LLM

Configurar exclusivamente en Render Environment o .env ignorado: `LLM_PROVIDER=groq`, `GROQ_API_KEY`, `GROQ_MODEL=openai/gpt-oss-20b`. Alternativamente `LLM_PROVIDER=gemini`, `GEMINI_API_KEY` y `GEMINI_MODEL`. Nunca introducir claves en la interfaz ni versionarlas.

| Variable | Finalidad | Valor por defecto |
|---|---|---|
| `LLM_PROVIDER` | `groq` o `gemini` | `groq` |
| `GROQ_API_KEY` / `GROQ_MODEL` | Credencial y modelo de Groq | vacío / `openai/gpt-oss-20b` |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Proveedor alternativo | vacío / `gemini-3.1-flash-lite` |
| `APP_API_KEY` | Acceso al historial y decisiones persistidas | vacío (privado deshabilitado) |
| `DATABASE_URL` | SQLite o PostgreSQL | `sqlite:///runtime/churn.db` |
| `LLM_DAILY_LIMIT` | Intentos de proveedor por día | `50` |
| `PUBLIC_LLM_DAILY_LIMIT` | Análisis públicos con LLM por día | `10` |
| `PORT` | Puerto del servidor | `8000` |

Las tres etapas usan respuestas estructuradas y validación semántica. El riesgo siempre procede de la red neuronal. Hasta 20 clientes de mayor riesgo reciben revisión LLM; todos los demás mantienen inferencia y recomendaciones por reglas explícitas. Si falla el proveedor, se informa sin simular respuestas exitosas. El aviso junto a Analizar explica el envío de indicadores sin códigos al proveedor.

Presupuesto predeterminado: 50 intentos de proveedor/día; 10 análisis públicos con LLM/día (`PUBLIC_LLM_DAILY_LIMIT`). Por análisis: una llamada predictiva, hasta dos de retención y una de supervisión. Límite total 60 segundos y 32 mensajes. Estos límites no garantizan disponibilidad o cuota del proveedor.

## Datos y API

CSV UTF-8 con coma o punto y coma, exactamente estas columnas:

```csv
cliente_id,antiguedad,compras_mensuales,monto_promedio,reclamos,dias_ultima_compra,pagos_atrasados
DEMO-001,24,5,800,2,30,1
```

`cliente_id` admite letras ASCII, números, guion y guion bajo; máximo 48 caracteres. Los conteos deben ser enteros no negativos. No se permiten nulos, NaN, infinito, duplicados ni campos adicionales. Hasta 300 filas y 256 KB; LLM para los 20 clientes de mayor probabilidad; el resto usa reglas. Se rechaza el lote completo si una fila es inválida. Fuera del dominio sintético se pide revisar los datos antes de actuar.

| Endpoint | Función | Acceso |
|---|---|---|
| `GET /health` | Estado de modelo y base | Público |
| `GET /api/config` | Configuración no sensible | Público |
| `GET /api/metrics` | Diagnóstico medido del artefacto | Público |
| `POST /api/demo` | Datos sintéticos fijos, sin persistencia | Público |
| `POST /api/public/analyze` | JSON: hasta 300 clientes, LLM con consentimiento, sin persistencia. `?stream=true` emite cada mensaje de la traza por SSE y al final el informe | Público |
| `POST /api/public/validate-csv` | Valida el CSV completo y devuelve 5 filas de vista previa, sin inferencia ni LLM | Público |
| `POST /api/public/analyze-csv` | CSV validado; `use_llm`, `consent` y `stream`; sin persistencia | Público |
| `POST /api/demo/llm` | Prueba LLM con ejemplos fijos y presupuesto limitado | Público |
| `POST /api/runs/{id}/approve-pending` | Acepta pendientes sin sobrescribir rechazos; no ejecuta acciones | Bearer |
| `POST /api/analyze` | JSON con `customers`, `use_llm`, `consent_external_processing`; admite `?stream=true` | Bearer |
| `POST /api/analyze-csv` | Cuerpo `text/csv`; opciones `use_llm`, `consent` y `stream` | Bearer |
| `GET /api/runs` | Últimas 100 ejecuciones | Bearer |
| `GET /api/runs/{id}` | Informe, traza y decisiones | Bearer |
| `POST /api/runs/{id}/decisions/{cliente_id}` | `{"decision":"approved"}` o `rejected` | Bearer |
| `GET /api/template.csv` | Plantilla de 12 clientes sintéticos | Público |

## Reproducir las verificaciones

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python scripts/evaluate.py
.\.venv\Scripts\python -m pytest -q --junitxml=evidence/tests.xml
node --check frontend/app.js
node tests/actions.cjs
node tests/clarity.cjs
# Con servidor local encendido:
.\.venv\Scripts\python scripts/collect_evidence.py
```

`evaluate.py` requiere Node para comparar con el original. Ejecutó 204 comparaciones con error máximo 5,55e-17. Sobre 1.000 ejemplos sintéticos nuevos: accuracy 92,7%, precisión 95,08%, recall 94,10%, F1 94,59%, AUC 0,9814. Son resultados diagnósticos; no pertenecen al test original ni prueban generalización real. Ver `models/evaluation.json` y `docs/AUDITORIA.md`.

El notebook original reportaba 92% de accuracy, pero su escalador no coincide con el exportado. Por tanto, no se atribuye esa métrica a esta versión. El procedimiento opcional `scripts/train.py`, con `requirements-training.txt`, entrena y exporta otro modelo en `models/retrained/`; no reemplaza automáticamente el servido. No ha sido ejecutado ni evaluado en esta entrega.

## Despliegue

Render es la opción principal. `Dockerfile` sirve frontend y backend en un solo servicio y `render.yaml` selecciona el plan Free. Seguir [la guía de publicación](docs/DESPLIEGUE.md). El contenedor incluye solo inferencia y runtime; no instala TensorFlow, NumPy ni pandas.

```powershell
docker compose up --build
```

Docker no está instalado localmente; Render construyó el contenedor y confirmó el servicio live. Compose persiste SQLite en un volumen. Render Free no ofrece disco persistente: configurar PostgreSQL externo con `DATABASE_URL` si las trazas deben sobrevivir reinicios. PostgreSQL está soportado por código pero su conexión no se ha probado con una instancia real.

## Estructura

```text
backend/      API, esquemas, red, agentes, proveedor LLM, almacenamiento
frontend/     Interfaz responsiva sin CDN ni proceso de compilación
models/       Pesos, escalador y evaluación medidos
data/         Demo, plantilla y diagnóstico sintéticos
scripts/      Inicio, exportación/evaluación, entrenamiento y evidencias
tests/        Pruebas de integración, seguridad y agentes
docs/         Auditoría, arquitectura, requisitos y despliegue
evidence/     Pruebas, traza, medidas y capturas LOCALES
original/     Referencias originales preservadas
runtime/      Base de datos local y temporales; excluidos de Git
```

El notebook original se conserva localmente y se excluye de publicación automática porque contiene metadatos de Colab y salidas históricas. `original/notebook-source.py` conserva el código para revisión; `scripts/train.py` ofrece el procedimiento reproducible sin sus salidas. No se afirma autoría de entrenamiento del equipo: el equipo debe confirmar ese dato.

## Documentos y límites pendientes

- [Auditoría técnica](docs/AUDITORIA.md)
- [Arquitectura, agentes y seguridad](docs/ARQUITECTURA.md)
- [Requisitos y aceptación](docs/REQUISITOS.md)
- [Guía Render y costos](docs/DESPLIEGUE.md)
- [Evidencias, casos de prueba y matriz A–K](docs/EVIDENCIAS.md)
- [Recorrido de evaluación](docs/RECORRIDO_PROFESOR.md)
- [Uso empresarial y límites](docs/USO_EMPRESARIAL.md)

Pendientes técnicos: validación con datos empresariales, almacenamiento durable y comprobación desde otro dispositivo. Groq cuenta con evidencia pública de respuestas válidas; el adaptador Gemini no tiene una generación exitosa acreditada.


## Recorrido para el profesor

Recorrido sin claves, paso a paso, en [RECORRIDO_PROFESOR.md](docs/RECORRIDO_PROFESOR.md). **Configuración → Probar LLM con ejemplos, sin clave** ejecuta tres casos ficticios con Groq y muestra intentos, duración, tokens y respuesta validada; los fallos se distinguen de una generación exitosa.

`POST /api/demo/llm` (alias `/api/demo/gemini`) solo admite fixtures internos: sin cuerpo ni parámetros, caché explícito de diez minutos, una ejecución concurrente y hasta cinco demostraciones nuevas por día con LLM, dentro del contador público diario y del presupuesto global.



## Experiencia de trabajo y calidad de datos

Inicio ofrece análisis individual o carga de cartera. Al elegir un CSV, `/api/public/validate-csv` valida todas las filas y devuelve cinco registros de vista previa sin inferencia, LLM ni persistencia. El análisis sigue usando el contrato validado completo. La interfaz evita envíos duplicados mientras hay una operación en curso.

Diagnóstico resume niveles de riesgo y permite filtrar. Recomendaciones muestra, por cliente, entrada, herramienta, salida, cobertura LLM y mensajes reales de cada agente. Aceptación conserva control humano y excluye observaciones del Supervisor de la aceptación masiva. La versión visible muestra resultados completados, no progreso ni razonamiento inventados.

Para un piloto empresarial faltan datos históricos reales con una definición y horizonte de abandono, evaluación temporal y calibración, identidad individual de revisores, almacenamiento durable e integración autorizada de tareas. El sistema actual no acredita reducción de churn ni pérdidas monetarias previstas.
