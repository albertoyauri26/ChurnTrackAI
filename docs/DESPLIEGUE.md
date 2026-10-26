# Publicación en Render y verificación

## Estado de publicación

Aplicación: https://churntrackai-4omr.onrender.com. Repositorio: https://github.com/albertoyauri26/ChurnTrackAI. Salud: https://churntrackai-4omr.onrender.com/health. Servicio Render `srv-dbekqo0ae00c73dfnj20`: Free, Docker, región Oregon, rama `master` (rama predeterminada del repositorio). Se creó el 24/10/2026 con la API de Render y sus variables equivalen a `render.yaml`; el commit `79a964f` quedó live ese día (`evidence/deployment.json`). Se desplegó como `a9c9345`; el 26/10/2026 se reescribieron solo los mensajes de tres commits en la rama `master`, con idéntico contenido. El despliegue original del equipo sigue en https://churntrackai.onrender.com (repositorio https://github.com/ManuelCarranzaAv/ChurnTrackAI). No se ha probado desde un segundo dispositivo físico.

## Elección de plataforma

Condiciones consultadas el 20 de octubre de 2026; revisar de nuevo al contratar.

| Opción | Recursos y restricciones relevantes | Decisión |
|---|---|---|
| Render Free | 512 MB, 0,1 CPU. Suspensión tras 15 min sin tráfico; reactivación cercana a un minuto. Disco efímero. 750 horas gratuitas por workspace/mes | Principal; un contenedor FastAPI para todo |
| Koyeb Free | 512 MB, 0,1 vCPU, 2 GB SSD; una instancia por organización, sin volumen; escala a cero tras 1 h | Alternativa Docker si está disponible para la cuenta |
| Vercel con funciones Python | Admite FastAPI; esta aplicación requiere adaptar la persistencia y los límites al entorno de funciones | Se conserva el despliegue funcional en Render |

Fuentes: [planes Render](https://render.com/docs/compute-plans), [servicios gratuitos Render](https://render.com/docs/free), [instancias Koyeb](https://www.koyeb.com/docs/reference/instances), [límites de funciones Vercel](https://vercel.com/docs/functions/limitations).

Render no recomienda sus instancias gratuitas para producción empresarial. El plan también tiene cuotas de transferencia y construcción; revisar su panel para evitar sobrecostos. No se implementan pings para impedir la suspensión. El frontend muestra reconexión y limita la espera a 70 segundos; no reenvía automáticamente un POST que pudo haber sido procesado.

## Preparar GitHub

1. Conectar GitHub en esta conversación o iniciar sesión en el navegador disponible. No transmitir tokens por chat.
2. Crear un repositorio del proyecto. Revisar `git status` y confirmar que `.env`, `runtime/`, `.venv/` y el notebook con metadatos quedan excluidos.
3. Publicar el código, modelos JSON, datos sintéticos y documentación. No incluir bases de datos con clientes.
4. Registrar la URL real del repositorio y el commit desplegado en `evidence/deployment.json` cuando existan.

Si se hace manualmente, tras crear el repositorio vacío y configurar Git local:

```powershell
git add backend frontend models data scripts tests docs evidence original .gitignore .dockerignore .env.example requirements.txt requirements-dev.txt requirements-training.txt requirements-lock.txt Dockerfile compose.yaml render.yaml pytest.ini README.md
git commit -m "Implementar plataforma B2B con inferencia y agentes auditables"
# Usar aquí la URL REAL devuelta por GitHub:
git remote add origin <URL_REAL_DEL_REPOSITORIO>
git push -u origin HEAD
```

No ejecutar marcadores `<...>` literalmente. Si ya hay un remoto, comprobarlo y actualizarlo sin sobrescribir repositorios ajenos. No se requieren GitHub Actions. Ambos servicios se vincularon por URL pública del repositorio. Aunque el servicio actual tiene `autoDeployTrigger=commit`, el push del 24/10/2026 no generó ningún despliegue porque Render no recibe eventos de GitHub sin su GitHub App. Para cada actualización: **Manual Deploy → Deploy latest commit** en el panel, o `POST /v1/services/srv-dbekqo0ae00c73dfnj20/deploys` con una clave de API de Render. Para despliegue automático, conectar GitHub en Render (Account Settings → Git) con acceso a este repositorio. Tras cada despliegue se verifica el commit publicado.

## Crear el servicio

1. En [Render Dashboard](https://dashboard.render.com), iniciar sesión.
2. Elegir **New → Blueprint** y conectar el repositorio con `render.yaml`. Alternativa: **New → Web Service**, repositorio, runtime Docker, plan Free y health check `/health`.
3. Comprobar el plan gratuito antes de confirmar. No añadir un disco ni un plan pagado sin decidir su costo.
4. `APP_API_KEY` se genera por Blueprint; para configuración manual generar una clave larga aleatoria y guardarla en Environment. Compartirla con el docente por un canal privado, no en README ni en video.
5. Configurar en Environment `LLM_PROVIDER=groq`, `GROQ_API_KEY` (panel seguro, nunca en el repositorio) y `GROQ_MODEL=openai/gpt-oss-20b`; `LLM_DAILY_LIMIT=50` y `PUBLIC_LLM_DAILY_LIMIT=10`. Alternativa: `LLM_PROVIDER=gemini` con `GEMINI_API_KEY` y `GEMINI_MODEL`.
6. Por defecto, `DATABASE_URL=sqlite:////app/runtime/churn.db`. Solo sirve para una demo descartable. Para conservar historial, reemplazar por la conexión segura PostgreSQL de una base externa. Se aceptan prefijos `postgres://`, `postgresql://` y `postgresql+psycopg://`. Usar TLS según las instrucciones del proveedor.
7. Desplegar. El contenedor usa el `PORT` de Render, escucha `0.0.0.0` y ejecuta un solo worker.
8. Revisar logs de build y servidor. El runtime no requiere descargar o entrenar modelos al arrancar.

Render Postgres gratuito expira a los 30 días y permite una base gratuita por workspace. No asumir almacenamiento permanente sin costo. Fuente: [Render Free](https://render.com/docs/free). La conexión PostgreSQL del proyecto necesita una prueba real tras configurarla.

## Verificar en la URL real

Guardar la URL literal que entregue Render. En una ventana independiente comprobar:

- `/health` responde 200, modelo loaded y base ok.
- Dashboard y estilos cargan por HTTPS; no depende de localhost ni CDN.
- Demo produce 12 predicciones, 4 clientes de riesgo alto y 6 mensajes en el modo de reglas con el artefacto actual.
- Configuración admite la clave; un cliente y el CSV generan resultados y el historial los recupera.
- Con Groq activado y consentimiento, la traza muestra llamada, JSON validado y consumo real. Confirmar `llm_report.status=validated`; un fallback no satisface esta verificación.
- Aprobar una recomendación; recargar el informe y comprobar que persiste sin acción externa.
- Exportar informe y CSV. Abrir el reporte de métricas y los factores.
- Repetir desde otro equipo o red; capturar pantallas de la URL pública y medir latencia online, incluida primera carga después de suspensión.

`scripts/collect_evidence.py` recopila medidas HTTP y traza sintética. El script distingue la URL pública de localhost y separa los archivos de evidencia; las verificaciones humanas de LLM, aprobación y otro dispositivo no quedan cubiertas por ese script.

## Actualizaciones

Cambiar código, ejecutar pytest y equivalencia del modelo si se tocaron sus artefactos, revisar secretos y subir el commit. Render puede desplegar automáticamente el branch conectado. Verificar `/health`, demo y traza después de cada build. Mantener el modelo y su evaluación juntos. Guardar exportaciones antes de reiniciar un servicio con SQLite efímero. Usar rollback desde Render ante un fallo y documentar el commit restaurado.

## LLM y presupuesto

Proveedor en producción: Groq, modelo `openai/gpt-oss-20b`. El 24/10/2026 figura como modelo de producción con soporte de `strict: true` en [modelos Groq](https://console.groq.com/docs/models) y [salidas estructuradas](https://console.groq.com/docs/structured-outputs). Tarifa publicada: USD 0,075 por millón de tokens de entrada y USD 0,30 por millón de salida.

Costo estimado a partir de tokens medidos en ejecuciones públicas reales (`usage` de cada informe) multiplicados por la tarifa publicada. No es una factura: el nivel gratuito de Groq no cobra, pero limita tokens y solicitudes por minuto.

| Consulta | Evidencia | Tokens entrada / salida | Costo por consulta | Costo por 100 consultas |
|---|---|---|---|---|
| 1 cliente, tres etapas | `evidence/three-agent-live.json` | 1.758 / 903 | USD 0,00040 | USD 0,040 |
| 300 clientes (20 con LLM), tres etapas | `evidence/redesign-verification.json` | 5.457 / 1.723 | USD 0,00093 | USD 0,093 |

Límites propios: 50 intentos de proveedor por día, 10 análisis públicos con LLM por día y como máximo 20 clientes por etapa. El 22/10/2026 un lote de 300 recibió HTTP 429 de Groq en Retención y Supervisor (`evidence/three-agent-batch-quota.json`). La aplicación lo informó, no reintentó y aplicó reglas. Render Free no tiene costo dentro de su cuota mensual.

Gemini sigue implementado como alternativa, pero no tiene una generación exitosa acreditada: las pruebas del 21/10/2026 devolvieron HTTP 503 o tiempo de espera agotado.

## ZIP y alternativas

El archivo ZIP de entrega conserva fuentes y artefactos para subir a un repositorio o construir una imagen Docker. Render se despliega desde Git o una imagen compatible; no asumir que acepta un ZIP como web completa. Koyeb puede construir el mismo Dockerfile con las variables indicadas. Subir únicamente HTML a un hosting estático no ejecuta esta API ni sus agentes.


## Acceso para el profesor

El enlace público permite analizar un cliente o el CSV de ejemplo de 300 clientes sintéticos sin clave; con consentimiento se consulta Groq dentro de la cuota pública diaria. Solo el guardado y la consulta del historial privado requieren validar APP_API_KEY mediante `/api/session`. GROQ_API_KEY permanece exclusivamente en el servidor. No compartir claves del proveedor.

Render Free no establece una caducidad fija para este servicio web: se suspende después de 15 minutos sin tráfico y vuelve a arrancar con una visita, normalmente en aproximadamente un minuto. Hay 750 horas gratuitas por espacio de trabajo y mes, además de cuotas de transferencia y compilación. El enlace puede compartirse mientras el servicio y la cuenta estén activos y dentro de cuota. SQLite se pierde al suspender, reiniciar o desplegar; exportar informes. No se ha contratado un plan de pago ni se promete disponibilidad continua. Fuente: https://render.com/docs/free (consultada 21/10/2026).

Vercel admite FastAPI/Python, pero migrar esta aplicación requiere adaptar almacenamiento y cuotas a funciones sin estado. Se conserva Render porque ya ejecuta el backend completo; el modo público reproducible permite la revisión académica. Fuente: https://vercel.com/docs/functions/runtimes/python .