# Requisitos y criterios de aceptación

Actores: docente/visitante (análisis temporal), analista autorizado (datos e informes), supervisor humano autorizado (decisiones) y proveedor LLM externo. La clave compartida distingue acceso público y administrativo; no identifica personas individuales.

| ID | Prioridad | Requisito | Agente o componente | Criterio verificable | Estado local |
|---|---|---|---|---|---|
| RF01 | P0 | Inferencia individual real | Predictivo | Devuelve probabilidad finita, riesgo y seis factores | Probado |
| RF02 | P0 | Inferencia por lote | Predictivo/API | CSV válido hasta 300 filas, orden de variables fijo | Probado |
| RF03 | P0 | Validación integral | API/Predictivo | Rechaza nulos, NaN, negativos, duplicados y formato inválido | Probado |
| RF04 | P0 | Delegación entre tres agentes | Supervisor | Misma ejecución registra predictivo, retención y supervisor | Probado |
| RF05 | P0 | Recomendación fundamentada | Retención | Acción y claves de evidencia pertenecen al catálogo permitido | Probado con reglas y dobles; evidencia pública por separado |
| RF06 | P0 | Control de coherencia y reparación | Supervisor | Detecta salida incompleta y solicita corrección | Probado |
| RF07 | P0 | LLM en tres etapas | Predictivo/Retención/Supervisor | Llamada externa exitosa con uso real y JSON validado | Verificado con Groq en producción (CP01, CP02 en EVIDENCIAS.md) |
| RF08 | P0 | Aprobación humana | API/DB | Decisión persistida e inmutable; no ejecuta acción externa | Probado |
| RF09 | P0 | Auditoría y recuperación | Supervisor/DB | ID, fechas, mensajes, herramientas y resultados recuperables | Probado SQLite |
| RF10 | P1 | Dashboard y segmentación | Frontend | KPI calculados, búsqueda, orden y filtros sobre resultados | Revisado en navegador |
| RF11 | P1 | Explicabilidad local | Predictivo | Seis diferencias por sustitución a la media, sin causalidad afirmada | Probado |
| RF12 | P1 | Informes exportables | Frontend | JSON de ejecución y CSV con protección de fórmulas | Implementado; revisión navegador |
| RF13 | P0 | Acceso a endpoints privados | API | Sin clave responde 401; análisis público no persiste; historial privado protegido | Probado |
| RF14 | P0 | Servicio HTTPS público | Render | URL verificada, `/health`, UI, modelo y tres agentes remotos | Publicado en Render |
| RF15 | P1 | Métricas reproducibles | Evaluación | Script genera matriz, ROC, baseline y comparación contra JS | Ejecutado |
| RF16 | P1 | Estado de agentes en vivo | Supervisor/Frontend | Con `?stream=true` cada mensaje de la traza llega por SSE antes del informe; la interfaz muestra pendiente, ejecutando, completado o error | Probado en local (CP07); pendiente de verificar en producción tras desplegar |

## Requisitos no funcionales

- Rendimiento objetivo del MVP: lote de 300 clientes en menos de 3 segundos sin LLM. En Render Free, seis lotes simultáneos de 300 terminaron en 11,5 s como máximo, es decir, unos 1,9 s por lote atendido en serie (CP11). Un lote de 300 con las tres etapas LLM tardó 4,7 s (CP01). No hay SLA.
- Disponibilidad: `/health` verifica red cargada y base accesible. No hay SLA académico ni disponibilidad medida durante semanas.
- Seguridad: secretos fuera del repositorio, claves en memoria del navegador, CSP, límites de tamaño, cuota, timeout y ausencia de acciones externas autónomas.
- Privacidad: códigos anónimos, sin datos libres ni identificadores enviados al LLM, consentimiento y demo sintética.
- Reproducibilidad: artefacto JSON, hash, dependencia fijada, scripts y pruebas. No se garantiza reconstruir los pesos originales desde el notebook discrepante.
- Mantenibilidad: seis módulos backend, contratos Pydantic y proveedor desacoplado. La interfaz usa HTML/CSS/JS sin framework para evitar un pipeline de compilación adicional.
- Portabilidad: Docker/Compose y PostgreSQL opcional. Docker construido en Render; conexión PostgreSQL no verificada.

## Alcance del MVP

Incluye carga manual, análisis, trazabilidad, selección de acciones, aprobación y exportación. Excluye integración CRM, envío de correos, facturación, gestión multiempresa, datos reales de entrenamiento, reentrenamiento automático y una política de identidad empresarial. El historial es historial de ejecuciones, no una serie temporal de abandono.

## Comparación con soluciones existentes

| Solución | Capacidad descrita por el proveedor | Diferencia verificable del MVP |
|---|---|---|
| Gainsight | Identificación de riesgo, salud del cliente y trabajo de retención | ChurnTrackAI expone pesos y trazas académicas; no replica sus integraciones ni valida superioridad |
| ChurnZero | Pronóstico de renovaciones, riesgo y agentes para customer success | Este MVP acota acciones a un catálogo y aprobación; no gestiona renovaciones reales |
| Totango | Salud del cliente y señales de riesgo combinando datos de clientes | Este MVP usa seis indicadores numéricos y un conjunto sintético; no integra fuentes empresariales |

Fuentes oficiales consultadas el 20 de octubre de 2026: [Gainsight](https://www.gainsight.com/solutions/customer-retention/), [ChurnZero](https://churnzero.com/customer-success-software/forecast-renewals-predict-churn/), [Totango](https://www.totango.com/outcomes/prevent-churn). No se compararon precios contratados ni exactitud mediante un benchmark común. La aportación es una demostración reproducible y auditable, no una afirmación de novedad comercial frente a esos productos.
