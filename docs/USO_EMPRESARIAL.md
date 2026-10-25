# Del prototipo a una operación de retención B2B

## Qué problema resuelve

Ayudar a un equipo comercial a decidir qué cuentas revisar, qué evidencia respalda esa prioridad y qué acción debe aprobar una persona. La unidad de trabajo es una cartera en una fecha de corte y una decisión por cliente, no una colección de gráficos.

## Recorrido implementado

1. **Inicio:** elegir demostración sintética o datos propios. Sin resultados todavía no se muestran paneles vacíos de métricas.
2. **Datos y análisis:** CSV como opción principal (hasta 300 clientes), cliente individual como alternativa. Una configuración compartida de reglas/LLM (Groq) y consentimiento aplica a ambos métodos.
3. **Diagnóstico:** lista de clientes, búsqueda, riesgo y prioridad. Distribuciones y comparaciones en una sección desplegable.
4. **Agentes:** seleccionar cliente y agente para inspeccionar indicadores, sensibilidad, acción, fuente y supervisión. Durante la ejecución, el estado de cada agente se actualiza con los mensajes que emite el servidor; al terminar se inspecciona la traza completa. No se simula actividad.
5. **Decisiones:** buscar cliente, filtrar pendientes/aprobadas/rechazadas y registrar revisión humana cuando el análisis está autenticado. La aprobación no equivale a contactar ni retener al cliente.
6. **Evaluación e historial:** evaluación del artefacto sintético e informes guardados, separados de la operación comercial.

## Responsabilidad de cada agente

| Agente | Entrada | Resultado | Límite |
|---|---|---|---|
| Predictivo | Seis indicadores por cliente | Probabilidad, nivel, factores y advertencias | Modelo sintético sin horizonte empresarial validado |
| Retención | Predicciones y catálogo de acciones admisibles | Selección de acción, evidencia y plan propuesto | LLM (Groq) opcional; reglas explícitas cuando no se utiliza o falla |
| Supervisor | Predicciones y recomendaciones | Consistencia, correcciones y traza | No valida efectividad comercial ni ejecuta acciones externas |
| Persona responsable | Evidencia y contexto del cliente | Aprobar o rechazar | La ejecución y el resultado comercial aún se registran fuera del MVP |

## Antes de un piloto con una empresa

- Acordar la definición de churn según su ciclo de compra: cancelación contractual o inactividad transaccional. Definir por separado el periodo de observación y el horizonte de predicción. Un ejemplo como «90 días sin comprar» debe validarlo el negocio; no es el objetivo entrenado por este prototipo.
- Obtener históricos de cuentas, pedidos, fechas, pagos y reclamos, con identificadores consistentes y un resultado de abandono comprobable. Construir indicadores solo con información disponible en la fecha de corte.
- Separar entrenamiento y evaluación por tiempo, comprobar posibles fugas de información y comparar con una regla sencilla de recencia. Medir precisión y recuperación en el grupo que el equipo realmente puede atender, además de calibración y rendimiento por segmento.
- Acordar capacidad de atención y costos de falsos positivos y negativos antes de fijar umbrales. No interpretar un índice comercial como pérdida monetaria esperada.
- Hacer primero un piloto supervisado, con responsable y resultado de cada intervención. Comparar resultados con una estrategia de referencia; no atribuir una recompra al sistema sin evidencia.
- Sustituir el acceso compartido por usuarios y roles, añadir separación por empresa, almacenamiento persistente, copias, auditoría, controles de datos y una política de conservación. Integrar el CRM solo después de definir permisos y aprobaciones.

## Medición de negocio propuesta (aún no implementada)

Registrar fecha de alerta, responsable asignado, contacto, respuesta, próxima acción, fecha de seguimiento y resultado observado. Distinguir alertas revisadas, clientes contactados, recompra observada y retención incremental. Los indicadores de ahorro o retorno requieren costos reales y una comparación adecuada.

## Estado honesto de esta versión

El flujo y la inspección de agentes son utilizables para una demostración y evaluación funcional. Cargar datos reales no convierte el modelo en un modelo validado para esa empresa. El límite de 300 clientes es por solicitud de inferencia, no una garantía de tamaño suficiente para entrenar. No hay conectores CRM, asignación de usuarios, seguimiento de intervenciones, evaluación temporal real ni persistencia garantizada en SQLite efímero.

Referencia primaria consultada el 21/10/2026: [Microsoft: definición, datos y evaluación de churn transaccional](https://learn.microsoft.com/en-us/dynamics365/customer-insights/data/predict-transactional-churn). Las cifras mínimas de ese producto no se trasladan como requisitos universales a este proyecto.

