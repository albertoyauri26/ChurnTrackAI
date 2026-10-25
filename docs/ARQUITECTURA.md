# Arquitectura actual

Frontend HTML/CSS/JS → FastAPI → Supervisor (orquestador) → Predictivo → Retención → Supervisor → revisión humana.

## Componentes y quién hace qué

| Componente | Qué hace | Qué no hace |
|---|---|---|
| Red neuronal (`backend/model.py`) | Calcula la probabilidad de churn con los pesos exportados de `modelo.js` (6–32–16–8–1) y la sensibilidad por sustitución a la media | No usa Groq; no se reentrena en producción |
| Agentes (`backend/agents.py`) | Clases Python con responsabilidades separadas que comparten `SharedState` y se envían mensajes Pydantic | No son tres modelos de IA distintos |
| Groq (`backend/llm.py`) | Proveedor de inferencia por API (`openai/gpt-oss-20b`). Cada agente lo consulta con su propio prompt y esquema JSON restringido | No calcula probabilidades, métricas ni factores; no ejecuta acciones |
| Persona revisora (frontend) | Acepta o rechaza cada propuesta | Ninguna aceptación envía correos ni modifica sistemas |

## Flujo multiagente

```mermaid
sequenceDiagram
    actor U as Usuario
    participant S as Supervisor (orquestador)
    participant P as Predictivo
    participant R as Retención
    participant N as Red neuronal
    participant L as Groq (LLM)
    U->>S: analysis_request (clientes validados)
    S->>P: delegate_prediction
    P->>N: inferencia + sustitución a la media
    P->>S: probabilidades, riesgo y factores
    P->>L: predictivo_llm_request (hasta 20, sin códigos)
    L-->>P: interpret_risk / review_data validado
    S->>R: delegate_retention
    R->>L: structured_selection_request (+ interpretación previa)
    L-->>R: acción y evidencia por cliente
    R->>S: recommendations (LLM o reglas)
    S->>S: validate(); si falla, request_correction → Retención con reglas
    S->>L: supervisor_llm_request (propuestas)
    L-->>S: approve_plan / request_review
    S->>U: validated_report (consolidado) → aceptación humana
```

Cada flecha corresponde a un mensaje real de `trace` con secuencia, hora, emisor, receptor, herramienta, estado y payload. Con `?stream=true` el servidor emite cada mensaje por SSE en cuanto se registra; la interfaz deriva de ellos el estado pendiente, ejecutando, completado o error de cada agente. El informe final contiene la traza completa.

## Agentes

| | Predictivo | Retención | Supervisor (orquestador) |
|---|---|---|---|
| Objetivo | Estimar el riesgo de cada cliente | Proponer una acción de retención fundamentada | Coordinar, validar y consolidar |
| Entrada | Seis indicadores validados | Riesgo, indicadores, acciones permitidas, interpretación del Predictivo | Solicitud, predicciones y propuestas |
| Herramientas | Validación Pydantic, red neuronal, sustitución a la media, Groq | Catálogo `ACTIONS`/`PLANS`, reglas `allowed()`/`rule_action()`, Groq | `validate()`, corrección, presupuesto, Groq |
| Salida estructurada | `Prediction` (probabilidad, riesgo, factores, avisos) + `interpret_risk`/`review_data` | `Recommendation` (acción, evidencia, plan, plazo, origen) | `approve_plan`/`request_review` + `validated_report` |
| Delegación | Recibe del Supervisor | Recibe del Supervisor tras la predicción | Delegación secuencial; una corrección si la validación falla |
| Errores | Fallo LLM → continúa con la red y lo registra | Hasta 2 intentos; sin reintento ante 400/401/403/404/429; luego reglas | Rechaza la ejecución si la corrección no pasa; límite de 60 s y 32 mensajes |
| Registro | `neural_inference_and_mean_ablation`, `predictivo_llm_*` | `structured_selection_request`, `validated_json`/`provider_call`, `recommendations` | `delegate_*`, `request_correction`, `supervisor_llm_*`, `validated_report` |

Qué se pierde al eliminar cada agente:

- **Predictivo:** no hay probabilidad ni factores. El LLM no puede reemplazarlo porque no ejecuta la red y tiene prohibido inventar riesgos.
- **Retención:** el riesgo queda sin una acción del catálogo, sin responsable, plazo ni criterio de verificación.
- **Supervisor:** nadie comprueba la correspondencia cliente–acción–evidencia, no se repara una salida incoherente y no se señalan propuestas para revisión adicional.

Por qué no basta un único prompt: la probabilidad procede de una red neuronal determinista y no del texto del LLM. Cada etapa tiene un esquema JSON con acciones distintas (`interpret_risk`, catálogo de retención, `approve_plan`), y cada salida se valida contra los datos del cliente antes de pasar a la siguiente. Un prompt único no separaría estas responsabilidades ni permitiría rechazar una etapa sin perder las demás. La evidencia `evidence/three-agent-rejected-before-fix.json` muestra un rechazo real del Predictivo mientras Retención y Supervisor siguieron validados.

## Controles

- Salida estructurada restringida por etapa (`strict: true` en Groq): acciones y claves de evidencia enumeradas, y validación posterior contra cada cliente.
- Al LLM solo se envían indicadores numéricos e índices; nunca códigos de cliente ni texto libre. Los datos se declaran como evidencia, nunca como instrucciones.
- Hasta 20 clientes priorizados por etapa reciben LLM; los 300 se procesan con la red y reciben una recomendación. Cada etapa declara su cobertura real.
- Presupuesto: `LLM_DAILY_LIMIT` (50 intentos/día) y `PUBLIC_LLM_DAILY_LIMIT` (10 análisis públicos/día, contador compartido con la demo de ejemplos fijos, que admite 5). Tiempo de espera de 12 s por llamada.
- Los fallos del proveedor se registran en el log del servidor solo con agente, intento, código y latencia; nunca la clave ni el cuerpo de la respuesta.
- Público: `/api/public/analyze` y `/api/public/analyze-csv` admiten LLM con consentimiento, sin persistencia ni clave administrativa. Privado: `/api/analyze`, historial y decisiones persistidas requieren `APP_API_KEY`. SQLAlchemy con SQLite y PostgreSQL configurable.
- «Aceptar todas» excluye `request_review` y no cambia decisiones ya tomadas. No hay RAG, memoria vectorial, CRM ni envío de correo. No hay identidad individual del revisor.
- La inferencia sin LLM no cede el bucle de eventos: con un worker, los análisis simultáneos se atienden en serie (medido en `evidence/http-measurements-public.json`). El límite de dos análisis concurrentes actúa durante las esperas de LLM.

Detalles de contratos, límites, pruebas y evidencia real en README.md, EVIDENCIAS.md y evidence/.
