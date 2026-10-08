# Servicio de análisis de solicitudes

Servicio en FastAPI que recibe solicitudes de soporte, las clasifica (categoría y prioridad), consulta los datos del cliente en un CRM externo cuando la prioridad es alta y propone una respuesta. El análisis es un grafo de LangGraph y cada resultado se guarda con SQLAlchemy junto con los tokens consumidos y su costo estimado.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/solicitudes/analizar` | Recibe `{"id", "texto", "cliente_id"}`, ejecuta el análisis, lo guarda y lo devuelve. |
| `GET` | `/solicitudes/{id}` | Devuelve el análisis guardado o `404` si no existe. |

Ejemplo de respuesta:

```json
{
  "id": "sol-1",
  "cliente_id": "cli-42",
  "texto": "No puedo acceder a mi cuenta desde ayer",
  "categoria": "tecnico",
  "prioridad": "alta",
  "respuesta_sugerida": "Hola, gracias por escribirnos. ...",
  "cliente_info": {"id": "cli-42", "nombre": "Cliente demo", "plan": "basico"},
  "tokens_entrada": 730,
  "tokens_salida": 45,
  "costo_estimado": 0.0001365,
  "creado_en": "2026-10-08T22:14:50.382775"
}
```

La documentación interactiva queda en `http://localhost:8000/docs`.

## Instalación

Requiere Python 3.11 o superior.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"          # agregar ",postgres" para usar PostgreSQL: ".[dev,postgres]"
cp .env.example .env             # opcional; sin .env se usan los valores por defecto
```

## Configuración

Todas las variables se leen del entorno o de un archivo `.env` local (que está en `.gitignore`).

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `CRM_URL` | `http://localhost:9000` | URL base del CRM externo. |
| `CRM_MAX_INTENTOS` | `3` | Intentos máximos por consulta al CRM. |
| `CRM_TIMEOUT_SEGUNDOS` | `2.0` | Tiempo máximo de respuesta por intento. |
| `CRM_BACKOFF_BASE` | `0.5` | Base del backoff exponencial, en segundos. |
| `DATABASE_URL` | `sqlite:///./solicitudes.db` | Conexión de SQLAlchemy. PostgreSQL: `postgresql+psycopg://usuario:clave@host:5432/base`. |
| `OPENAI_API_KEY` | vacío | Si está definida se usa `ChatOpenAI`; si no, un modelo fake. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modelo de OpenAI. |
| `PRECIO_INPUT_POR_MILLON` | `0.15` | Precio en USD por millón de tokens de entrada. |
| `PRECIO_OUTPUT_POR_MILLON` | `0.60` | Precio en USD por millón de tokens de salida. |

La clave de OpenAI solo vive en el `.env` local; nunca se versiona.

## Ejecución local

En una terminal, el CRM simulado (falla el 30 % de las veces con 429 o 500):

```bash
uvicorn mock_crm:app --port 9000
```

En otra, la API:

```bash
uvicorn app.main:app --port 8000
```

Prueba rápida:

```bash
curl -X POST http://localhost:8000/solicitudes/analizar -H "Content-Type: application/json" -d '{"id":"sol-1","texto":"No puedo acceder a mi cuenta desde ayer","cliente_id":"cli-42"}'
curl http://localhost:8000/solicitudes/sol-1
```

## Docker

```bash
docker build -t analisis-solicitudes .
docker run -p 8000:8000 -e CRM_URL=http://host.docker.internal:9000 analisis-solicitudes
```

La imagen corre con un usuario sin privilegios y guarda la base SQLite en `/app/data` (se puede montar un volumen ahí o pasar un `DATABASE_URL` de PostgreSQL). Para usar OpenAI dentro del contenedor: `docker run --env-file .env ...`. El `.env` nunca se copia a la imagen (`.dockerignore`).

## Entorno de pruebas con Docker Compose

`docker-compose.yml` levanta el servicio completo: la API, el CRM simulado y PostgreSQL.

```bash
docker compose up -d --build --wait
python scripts/demo.py
```

- `--wait` espera a que la API responda (tiene un healthcheck) antes de devolver el control.
- La API queda en `http://localhost:8000` (documentación en `/docs`) y el CRM simulado en `http://localhost:9000`.
- Dentro de la red de Compose la API usa `CRM_URL=http://crm:9000` y PostgreSQL; estos valores tienen prioridad sobre el `.env`.
- Si existe un `.env` con `OPENAI_API_KEY`, la API usa OpenAI; si no, el modelo fake.
- `scripts/demo.py` envía cuatro solicitudes de ejemplo (facturación, comercial, técnica y un intento de inyección de prompt), muestra la clasificación, los datos del CRM, los tokens, el costo y la respuesta, y prueba el `GET` y el `404`.
- Los reintentos del CRM se ven en `docker compose logs api` (líneas `CRM attempt ... retrying`).
- Para inspeccionar la base: `docker compose exec db psql -U solicitudes -d solicitudes -c "select * from analisis;"`.
- Para detener todo y borrar los datos: `docker compose down -v`.

## Pruebas

```bash
pytest -q
```

Las pruebas no necesitan el CRM simulado ni una clave de OpenAI: las respuestas HTTP se simulan con `respx`, el modelo es un `FakeListChatModel` y la base es SQLite en memoria. El `conftest.py` desactiva la lectura del `.env` antes de importar la aplicación, así que siempre corren en modo fake aunque exista una clave local.

- `tests/test_graph.py`: prioridad alta consulta el CRM y la respuesta recibe los datos del cliente; prioridad baja no lo consulta; un CRM caído no detiene el análisis; el texto de la solicitud no puede cerrar su bloque de datos.
- `tests/test_retry.py`: éxito al tercer intento con backoff 0.5 s y 1 s; agotamiento de intentos ante 429; un timeout se reintenta; un 404 no se reintenta.
- `tests/test_api.py`: el análisis se persiste y se recupera; reenviar el mismo `id` lo actualiza; un `id` inexistente da 404.
- `tests/test_persistence.py`: sin datos del cliente, `cliente_info` queda como `NULL` de SQL y no como el valor JSON `null`.

## Decisiones de diseño

**Forma del grafo.** `clasificar → (prioridad == "alta" ? consultar_cliente : proponer_respuesta) → proponer_respuesta → END`. La bifurcación es una arista condicional sobre la clasificación ya validada, así el camino lo decide el código y no el modelo. `build_graph(llm, crm_client)` recibe sus dependencias para poder probarlo con un modelo fake y un CRM simulado.

**Llamada directa al CRM dentro del nodo.** No uso tool calling: la regla "consultar el CRM solo si la prioridad es alta" es determinista, así que dejarla en manos del modelo agregaría costo, latencia y una fuente de error sin ningún beneficio.

**Política de reintentos.** Reintento ante 429, 5xx, timeouts y errores de conexión, porque son fallas transitorias. Otros 4xx (por ejemplo 404) fallan de inmediato porque repetir la llamada no cambia la respuesta. El backoff es exponencial (`base * 2**intento`: 0.5 s y 1 s con los valores por defecto), con un máximo de intentos y un timeout por intento. En el peor caso la consulta tarda `3 × 2 s + 1.5 s = 7.5 s`. Si se agotan los intentos el cliente lanza `CRMUnavailable`, el nodo lo captura, deja `cliente_info = None` y el análisis sigue: la respuesta se genera sin personalizar en vez de fallar la solicitud entera. La función `sleep` es inyectable para que las pruebas corran al instante.

**Upsert por `id`.** El `id` de la solicitud es la clave primaria. Reenviar el mismo `id` reprocesa y actualiza el análisis existente (conservando `creado_en`), de modo que un cliente que reintenta un POST no genera duplicados ni errores. La alternativa era responder `409`; preferí que la operación sea idempotente en cuanto a estado.

**Modelo real o fake con una sola interfaz.** `get_llm()` devuelve `ChatOpenAI` si hay clave y un `FakeListChatModel` con respuestas JSON fijas si no. Los nodos no saben cuál reciben: ambos pasan por `invoke_structured()`, que usa `with_structured_output(..., include_raw=True)` cuando el modelo lo soporta (así conservo el uso de tokens del mensaje crudo) y, si el modelo lanza `NotImplementedError` como el fake, agrega las instrucciones de formato de `PydanticOutputParser` al prompt y valida el JSON devuelto. En ambos casos el resultado es una instancia validada de Pydantic (`Clasificacion` con `Literal` para categoría y prioridad). La respuesta sugerida también se pide como JSON (`RespuestaSugerida`) para tratar los dos pasos igual. El fake guarda un cursor interno sobre sus respuestas, por eso creo una instancia por solicitud. Si el modelo devuelve algo que no valida, la API responde `502`.

**Conteo de tokens y costo.** Uso `usage_metadata` cuando el modelo lo reporta (OpenAI). El fake no lo reporta, así que estimo con `tiktoken` (`cl100k_base`) sobre el prompt completo, incluidas las instrucciones de formato, y la salida. Si la codificación no está disponible (tiktoken la descarga la primera vez) uso una aproximación por palabras para no fallar sin red; en la imagen de Docker la codificación queda descargada en el build. Los tokens se acumulan entre las dos llamadas al modelo con un reducer de suma en el estado del grafo. El costo es `entrada/1e6 × precio_entrada + salida/1e6 × precio_salida`, con precios configurables y redondeado a 8 decimales.

**Higiene de prompts.** El texto de la solicitud y los datos del CRM son datos de terceros: van dentro de bloques `<solicitud>` y `<cliente>`, el prompt de sistema indica que nunca se sigan instrucciones contenidas en ellos y elimino esas etiquetas del contenido para que no pueda cerrar su propio bloque. Además, la salida está restringida por el esquema de Pydantic, así que una inyección no puede producir una categoría o prioridad fuera de las permitidas. No es una defensa absoluta, pero reduce bastante la superficie.

**Endpoints síncronos.** El grafo, el cliente HTTP y SQLAlchemy son bloqueantes, así que declaré los endpoints con `def` para que FastAPI los ejecute en su pool de hilos sin bloquear el event loop.

**Persistencia.** SQLAlchemy 2 con un motor creado desde `DATABASE_URL`; para SQLite agrego `check_same_thread=False`. Las tablas se crean en el `lifespan` de FastAPI. `cliente_info` usa `JSON(none_as_null=True)` para que la ausencia de datos del cliente se guarde como `NULL` de SQL (por defecto SQLAlchemy guarda el valor JSON `null`, y entonces `WHERE cliente_info IS NULL` no encuentra esas filas). El driver de PostgreSQL (`psycopg[binary]`) es un extra opcional del paquete y viene instalado en la imagen de Docker.

## Pendiente y lo que haría con más tiempo

- **Migraciones con Alembic** en lugar de `create_all` al arrancar, para poder evolucionar el esquema sin perder datos.
- **Versión asíncrona** (`httpx.AsyncClient`, `graph.ainvoke`, SQLAlchemy async) si el volumen de solicitudes concurrentes lo justifica; hoy el pool de hilos es suficiente y el código es más simple.
- **Jitter en el backoff y circuit breaker** para el CRM: con varias instancias reintentando al mismo tiempo, el jitter evita picos sincronizados y el circuit breaker deja de llamar a un CRM caído por un tiempo.
- **Plazo total para la consulta al CRM**, además del timeout por intento, si hubiera un SLA de respuesta del endpoint.
- **Reintento ante salidas inválidas del modelo** (por ejemplo, reenviar el error de validación al modelo una vez) antes de responder `502`.
- **Zona horaria en SQLite:** SQLite no guarda zona horaria, así que `creado_en` vuelve sin ella; en PostgreSQL se conserva. Con más tiempo normalizaría a UTC explícito al leer.
- **Autenticación, rate limiting y observabilidad** (logs estructurados y trazas del grafo), necesarios antes de exponer el servicio.
- **Evitar que la respuesta sugerida invente datos.** Al probar con OpenAI (`gpt-4o-mini`), ante una consulta comercial sobre el plan premium el modelo inventó un precio (USD 29.99 al mes) y beneficios del plan, aunque el prompt ya pide no inventar datos. Haría la instrucción explícita (no mencionar precios, beneficios, plazos ni compromisos que no estén en los datos del cliente y, en su lugar, derivar al área correspondiente) y agregaría una prueba con ese caso. Como la respuesta es una sugerencia para un agente humano y no se envía automáticamente, el riesgo hoy es acotado.

## Notas sobre el enunciado

