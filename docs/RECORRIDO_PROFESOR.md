# Recorrido de evaluación sin claves

1. Abrir https://churntrackai.onrender.com/. La primera visita puede tardar cerca de un minuto si Render Free suspendió el servicio.
2. En **Inicio**, dejar **Un cliente** con los valores sugeridos o elegir **Cartera de clientes**, descargar «Ejemplo de 300 clientes sintéticos» y cargarlo. La vista previa valida todas las filas sin ejecutar el modelo ni consultar el LLM.
3. Pulsar **Analizar churn**. Mientras el servidor trabaja, el panel muestra Supervisor (orquestador), Predictivo y Retención como pendiente, ejecutando, completado o error. Cada cambio corresponde a un mensaje real que el backend emite al registrarlo.
4. **Diagnóstico**: riesgo alto, medio y bajo, probabilidad por cliente y factores por sustitución a la media. Son asociaciones del modelo, no causas.
5. **Recomendaciones**: elegir un cliente y alternar entre los tres agentes. Se ve qué recibió, qué herramienta usó y qué entregó cada uno, si la respuesta del LLM se validó o se usaron reglas, el proveedor y modelo, y los mensajes intercambiados. «Ver evidencia de las consultas al LLM» muestra la solicitud sin códigos y la respuesta validada; «Descargar informe y traza JSON» exporta la ejecución completa.
6. **Aceptación**: aceptar o rechazar cada propuesta, o aceptar todas las pendientes elegibles. Las marcadas por el Supervisor con `request_review` quedan fuera. «Preparar documento de seguimiento» y «Descargar plan de seguimiento CSV» generan archivos reales; no se envían mensajes ni se crean tareas externas.
7. **Configuración → Probar LLM con ejemplos, sin clave** ejecuta tres casos fijos del servidor y muestra intentos, duración, tokens y respuesta validada, o el fallo real del proveedor.

## Límites y evidencia

- El análisis público no se guarda. Solo el historial privado requiere APP_API_KEY.
- Groq recibe únicamente los seis indicadores numéricos e índices de hasta 20 clientes priorizados, nunca códigos de cliente. El LLM elige acciones del catálogo; no calcula el riesgo ni redacta los planes.
- Cuotas: 10 análisis públicos con LLM por día (compartidos con la prueba de ejemplos fijos, que admite 5), 50 intentos de proveedor por día. Si se agotan, la ejecución lo indica y usa reglas explícitas.
- `POST /api/demo/llm` (alias histórico `/api/demo/gemini`) acepta solo los ejemplos del servidor, rechaza cuerpo y parámetros, ejecuta una demostración a la vez y reutiliza el resultado durante 10 minutos indicándolo.
- Un fallo del proveedor se muestra explícitamente y los agentes continúan con reglas; nunca se presenta como respuesta del LLM.

Verificación automatizada: `pytest` (64 pruebas), `node tests/actions.cjs` y `node tests/clarity.cjs`. Resultados en [EVIDENCIAS.md](EVIDENCIAS.md).
