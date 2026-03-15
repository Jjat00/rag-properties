# RAG Properties — Instrucciones del Proyecto

## Objetivo

Sistema RAG para búsqueda semántica de propiedades inmobiliarias en México.
El usuario puede buscar propiedades en lenguaje natural (ej: "casa de 4 habitaciones con 2 baños en Cancún")
y el sistema retorna las propiedades más relevantes del catálogo.

**Dos modos de uso:**
1. **Chat conversacional** (vista principal): Agente multi-turno con LangGraph ReAct + Gemini 3 Flash. Busca propiedades, presenta resultados y hace preguntas dirigidas cuando hay ambigüedad. SSE streaming token por token.
2. **Playground** (búsqueda single-shot): Query directo con analytics (distribución de scores, gráfica de similitud, comparación de modelos A/B).

**Flujo principal (compartido por ambos modos):**
1. Ingesta: Leer Excel de propiedades → canonicalizar ubicaciones → generar embeddings → almacenar en Qdrant
2. Búsqueda: Query en lenguaje natural → normalizar ubicaciones → extraer filtros con LLM → pre-filtrar metadata → búsqueda vectorial dense con query completo → desambiguación automática → resultados

---

## Stack tecnológico

- **Lenguaje**: Python 3.12 (backend)
- **Package manager**: `uv` — SIEMPRE usar uv, nunca pip directamente
- **Vector DB**: Qdrant (local Docker en desarrollo, Qdrant Cloud en producción)
- **Embeddings**: Gemini gemini-embedding-001 (default) + OpenAI text-embedding-3 small/large (multi-modelo, intercambiables)
- **Query parsing**: Gemini 3 Flash con structured output para extraer filtros
- **Agente conversacional**: LangGraph (ReAct) + Gemini 3 Flash con tool calling
- **Streaming**: SSE (Server-Sent Events) para chat en tiempo real
- **LLM credits**: Gemini y OpenAI (NO Anthropic). Nunca usar APIs de Anthropic.
- **Self-hosted**: NADA self-hosted. Solo APIs y servicios managed.
- **Backend**: FastAPI + LangGraph (chat multi-turno) + sse-starlette (streaming)
- **Frontend**: React 19 + Vite + Shadcn/ui + Tailwind v4 (dos vistas: Chat y Playground)
- **Deploy**: Railway (backend) + Vercel (frontend) + Qdrant Cloud
- **Fecha de inicio**: 16 de febrero de 2026

---

## Reglas de desarrollo

### Python y entorno virtual
- **SIEMPRE usar `uv`** como manejador de paquetes. Nunca usar `pip install` directamente.
- El proyecto Python vive en `backend/` con su propio `pyproject.toml` y `.venv`
- Activar el entorno virtual antes de ejecutar cualquier script:
  ```bash
  cd backend && source .venv/bin/activate
  ```
- Para instalar dependencias: `cd backend && uv add <paquete>`
- Para ejecutar scripts: `cd backend && uv run python script.py` o con el venv activado
- Los imports son absolutos desde `backend/` como raíz (ej: `from config import settings`)

### Qdrant
- Usar Qdrant **local** via Docker durante desarrollo
- Puerto por defecto: `6333` (HTTP) y `6334` (gRPC)
- **Usar siempre `qdrant/qdrant:latest`** — el client v1.17+ requiere server v1.17+
- Arrancar con: `docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant:latest`

### Código
- Usar **type hints** en todas las funciones Python
- Preferir **async/await** en FastAPI
- Usar **Pydantic** para validación de datos
- Variables de entorno en `.env` (nunca hardcodear credenciales)

---

## Estructura del proyecto

```
rag-properties/
├── CLAUDE.md
├── README.md
├── plan.md                         # Plan de fases y decisiones
├── data/
│   └── properties.xlsx             # Excel fuente de datos
├── backend/
│   ├── pyproject.toml              # Dependencias (uv)
│   ├── uv.lock
│   ├── .venv/
│   ├── .env                        # Variables de entorno (no commitear)
│   ├── .env.example
│   ├── config.py                   # Settings, enum de modelos, dimensiones
│   ├── main.py                     # FastAPI app + endpoints (search, chat SSE)
│   ├── models/
│   │   └── property.py             # Modelo Pydantic de propiedad
│   ├── agent/                      # Agente conversacional (LangGraph)
│   │   ├── state.py                # AgentState (MessagesState + campos de búsqueda)
│   │   ├── prompt.py               # System prompt del agente
│   │   ├── tools.py                # Tool search_properties (wrappea Searcher)
│   │   ├── graph.py                # ReAct graph: agent → tools → loop
│   │   └── session.py              # SessionManager in-memory
│   ├── embeddings/
│   │   ├── base.py                 # Clase abstracta EmbeddingProvider
│   │   ├── openai_provider.py      # OpenAI text-embedding-3-small/large
│   │   ├── gemini_provider.py      # Gemini gemini-embedding-001
│   │   └── registry.py             # Registry con cache de providers
│   ├── vectorstore/
│   │   └── qdrant_manager.py       # Gestión de colecciones e indexes
│   ├── ingestion/
│   │   ├── location_normalizer.py  # Diccionario estático de aliases MX
│   │   ├── excel_loader.py         # Leer y parsear Excel
│   │   └── indexer.py              # Generar embeddings e indexar en Qdrant
│   └── search/
│       ├── location_normalizer.py  # Diccionario de aliases MX
│       ├── query_parser.py         # LLM structured output → ParsedQuery
│       └── searcher.py             # Búsqueda semántica con filtros
├── frontend/                       # React 19 + Vite + Shadcn (Chat + Playground)
│   └── src/
│       ├── components/
│       │   ├── chat/               # Vista Chat (split-screen)
│       │   │   ├── chat-view.tsx   # Layout 60/40 (chat + propiedades)
│       │   │   ├── chat-panel.tsx  # Lista de mensajes + input
│       │   │   ├── chat-input.tsx  # Textarea + enviar
│       │   │   ├── chat-message.tsx # Burbujas con markdown
│       │   │   └── properties-panel.tsx # Panel derecho con resultados
│       │   ├── search/             # Barra de búsqueda (playground)
│       │   ├── results/            # Cards de propiedades (compartido)
│       │   └── analytics/          # Gráficas de similitud (playground)
│       ├── hooks/
│       │   ├── use-chat.ts         # Estado del chat + streaming
│       │   └── use-search.ts       # Estado de búsqueda (playground)
│       ├── lib/
│       │   ├── chat-api.ts         # SSE stream parser con callbacks
│       │   └── api.ts              # API client REST
│       └── types/
│           └── api.ts              # Tipos compartidos
└── data/                           # Excel de propiedades
```

---

## Esquema de datos — Propiedades

Columnas del Excel fuente:

| Campo Excel | Descripción |
|-------------|-------------|
| `ID` | Identificador único de la propiedad |
| `Agent: FirstName` | Nombre del agente |
| `Agent: LastName` | Apellido del agente |
| `Agent: Company: Name` | Empresa del agente |
| `AgentSeller: Phone` | Teléfono del agente |
| `Listing: Price: Currency` | Moneda del precio (ej: MXN) |
| `Listing: Price: Price` | Precio de la propiedad |
| `Type` | Tipo de propiedad (Casa, Terreno comercial, Casa en condominio, etc.) |
| `Listing: Operation` | Tipo de operación (sale, rent, etc.) |
| `Listing: Title` | Título del anuncio |
| `InternalId` | ID interno (ej: CQC-063) |
| `Address: Neighborhood: Name` | Colonia/Fraccionamiento |
| `Address: PublicStreet` | Dirección completa |
| `Address: State: Name` | Estado |
| `Address: City: Name` | Ciudad |
| `Attributes: Suites` | Número de recámaras/suites |
| `Attributes: Bathrooms` | Número de baños |
| `Attributes: RoofedSurface` | Superficie techada (m²) |
| `Attributes: Surface` | Superficie total (m²) |
| `Attributes: Condition` | Condición (Bueno, Excelente, etc.) |
| `Address: Name` | Nombre de referencia de la dirección |

**Volumen**: 8,808 filas en Excel (8,803 únicas tras deduplicar 5 IDs repetidos), escalable a 100K+.
**IDs**: Strings hexadecimales (ej: `68f2e999d0e6dd4c13fe9da9`), no integers.

---

## Estrategia de embeddings

### Texto para embedding
El Title es el campo con mayor valor semántico (escrito por humanos para describir la propiedad).
El template prioriza Title primero, luego contexto estructurado como fallback:

```
{Title}. {Type} en {operation} en {Neighborhood}, {City}, {State}.
{Bedrooms} recámaras, {Bathrooms} baños, {Surface}m².
Condición: {Condition}.
```

**Incluido en embedding**: Title, Type, operation, Neighborhood, City, State, Bedrooms, Bathrooms, Surface, Condition.
**Excluido del embedding** (solo en payload): precio (filtro exacto es mejor), dirección cruda (ruido), datos del agente.
**Manejo de nulls**: Omitir el fragmento si el campo es null, nunca embeddear "None" o "N/A".

### Un solo vector por propiedad
- Los filtros de metadata ya separan por aspecto (ciudad, recámaras, precio)
- Named vectors (location vs description) no se justifican: ubicación y descripción están correlacionados semánticamente
- Aplica tanto para 8K como para 100K+ propiedades

### Una colección por modelo de embedding
- Qdrant requiere dimensiones uniformes por colección
- Permite A/B testing limpio entre modelos
- Consolidar a una sola colección después de determinar el modelo ganador

### Qué embeddear del query del usuario
**Siempre embeddear el query COMPLETO del usuario**, no solo el residuo semántico después de extraer filtros.
Los filtros ya restringen los candidatos en Qdrant; la redundancia en el embedding no daña.

### Direcciones: NO en embedding, SÍ en payload
Las direcciones crudas ("Av. 5, C. 19 Colonia Tumben Kaa norte-Región 012") son ruido para el embedding.
Se guardan en payload para mostrar en resultados. El Neighborhood sí entra al embedding porque los usuarios
buscan por colonia/zona de forma descriptiva.

---

## Normalización de ubicaciones (México)

### Problema
Los usuarios escriben ubicaciones de formas muy variables:
- "Edo. de México" / "Estado de México" / "Edomex" / "EdoMex"
- "CDMX" / "Ciudad de México" / "DF" / "D.F."
- "Q. Roo" / "Quintana Roo" / "QRoo"
- "Playa" / "Playa del Carmen" / "PDC"

Los filtros keyword de Qdrant son exact-match, así que la normalización es obligatoria.

### Doble capa de normalización

**Capa 1 — Diccionario estático** (`location_normalizer.py`):
- Mapea variantes comunes a nombres canónicos (costo cero, cubre 95%)
- Se aplica tanto en ingesta (canonicalizar datos del Excel) como en query time
- Los nombres canónicos deben salir de auditar el Excel: `df["Address: City: Name"].value_counts()`

**Capa 2 — LLM parser** (Gemini 3 Flash):
- Resuelve casos ambiguos ("México" solo → Ciudad o Estado según contexto)
- Normaliza variantes no cubiertas por el diccionario
- El system prompt incluye la lista de nombres canónicos del catálogo

### Gotchas de México
- **"México" es ambiguo**: default al más común en los datos
- **Acentos inconsistentes**: canonicalizar en ingesta ("Cancun" → "Cancún")
- **Municipio vs ciudad**: "Benito Juárez" vs "Cancún" — usar `MatchAny` con variantes
- **"Playa" solo**: resolver a "Playa del Carmen" solo si contexto Q. Roo
- **Colonias sin estándar**: NO filtrar por keyword, dejar al embedding semántico

### Indexes en Qdrant
- `city` → keyword (exact match tras normalización)
- `state` → keyword (exact match tras normalización)
- `neighborhood` → text (full-text index para partial matching)
- `address` → text (MULTILINGUAL tokenizer, min 2, max 30) — para MatchText de calles
- `title` → text (MULTILINGUAL tokenizer, min 2, max 30) — para MatchText de keywords en título

---

## Estrategia RAG — Decisiones de arquitectura

### LangGraph para chat, FastAPI para playground
- **Chat conversacional**: LangGraph ReAct con MemorySaver — multi-turno justifica el framework (loop tool-calling, checkpointer, streaming)
- **Playground**: FastAPI simple — búsqueda single-shot no necesita agente ni memoria
- El agente wrappea el MISMO pipeline de búsqueda (QueryParser → Searcher) que usa el playground

### Modelos

#### Embeddings (intercambiables)

| Modelo | Dimensiones | Colección Qdrant | Costo | Default |
|--------|------------|------------------|-------|---------|
| `gemini` | 3072 | `properties_gemini` | $0.15/M tokens | **Sí** |
| `openai-small` | 1536 | `properties_openai_small` | $0.02/M tokens | No |
| `openai-large` | 3072 | `properties_openai_large` | $0.13/M tokens | No |

- Todos via API, **nada self-hosted**
- Cosine similarity para todos
- El modelo activo se configura via `.env` (`DEFAULT_EMBEDDING_MODEL=gemini`) o parámetro en el endpoint
- Esto permite A/B testing de calidad de resultados

#### LLMs

| Uso | Modelo | Provider |
|-----|--------|----------|
| Query parsing | `gemini-3-flash-preview` | Google Gemini |
| Agente conversacional | `gemini-3-flash-preview` | Google Gemini |

### Arquitectura del agente conversacional

```
┌─────────────────────────────────────────────────┐
│  POST /chat (SSE)                               │
│                                                 │
│  User message                                   │
│       ↓                                         │
│  ┌─────────┐    tool_calls?    ┌──────────┐     │
│  │  Agent   │ ──────────────→  │  Tools   │     │
│  │ (Gemini  │ ←──────────────  │ (search) │     │
│  │  3 Flash)│   tool results   └──────────┘     │
│  └─────────┘                                    │
│       ↓ no tool_calls                           │
│  Response (streaming SSE)                       │
│       ↓                                         │
│  Frontend: chat panel + properties panel        │
└─────────────────────────────────────────────────┘
```

**Grafo ReAct (LangGraph):**
- `START` → `agent_node` (Gemini 3 Flash con tools)
- `agent_node` → `should_continue?`
  - Tiene `tool_calls` → `tool_node` (ejecuta search) → `agent_node` (loop)
  - No tiene `tool_calls` → `END` (responde al usuario)

**Tool `search_properties`:**
- Wrappea el pipeline completo: QueryParser → Searcher (normalización → filtros → embed → vector search → desambiguación)
- Retorna JSON con: results, parsed_filters, disambiguation, state_results, metrics
- El agente recibe un resumen + datos para razonar; el frontend recibe resultados completos via SSE

**Memoria:**
- `MemorySaver` (LangGraph in-memory checkpointer) por `thread_id` = `session_id`
- Acumula contexto entre turnos: "terreno en el centro" + "en Quintana Roo" → "terreno en el centro en Quintana Roo"

**Reglas clave del agente:**
- El agente NUNCA reformula el query del usuario. Pasa el texto EXACTO al tool `search_properties`.
- El parser downstream (QueryParser) se encarga de interpretar ubicaciones, abreviaciones, calles, etc.
- El agente NUNCA ofrece acciones que no puede realizar: fotos, agendar visitas, contactar agentes, emails, WhatsApp. Solo puede buscar y presentar datos del catálogo.

**SSE Events emitidos por `/chat`:**

| Evento | Data | Propósito |
|--------|------|-----------|
| `session` | `{session_id}` | ID de sesión para continuidad |
| `token` | string | Token de texto del LLM (streaming) |
| `tool_start` | `{name, args}` | El agente invoca búsqueda |
| `results` | `PropertyResult[]` | Resultados de búsqueda |
| `filters` | `ParsedQuery` | Filtros extraídos |
| `disambiguation` | `DisambiguationInfo[]` | Datos de desambiguación |
| `state_results` | `{estado: PropertyResult[]}` | Resultados por estado |
| `metrics` | `SearchMetrics` | Métricas de la búsqueda |
| `done` | `""` | Stream completo |
| `error` | string | Error |

### Estrategia de búsqueda: unified must + semántica

```
Query usuario
    → Capa 1: Diccionario estático normaliza ubicaciones (múltiples ciudades soportadas)
    → Capa 2: LLM parser extrae filtros + query semántico
       - cities[], neighborhoods[], property_types[] (listas para multi-valor)
       - street (calle detectada en el query)
       - Prompt basado en datos reales del catálogo (80 colonias top, calles frecuentes, municipios)
    → Qdrant filtra con must unificado:
       - must: city (MatchAny), state, property_type (MatchAny), operation, rangos numéricos
       - must (texto): Filter(should=[address, neighborhood, title] MatchText) para street y neighborhoods
         → Busca en los 3 campos TEXT con OR: no importa si el LLM clasifica como calle o colonia
    → Desambiguación automática:
       - Estado: facet() descubre estados, pre-fetch top-K por estado, conteos reales (no catálogo)
       - Colonia: conteo desde resultados cuando hay street
       - Tipo: count() por variante cuando hay aliases expandidos
    → Búsqueda vectorial dense con query COMPLETO del usuario
    → Retorna top-k propiedades + total real (count Qdrant, no len) + state_results pre-fetched con conteos reales por estado
```

**Filtros de texto (street/neighborhoods)**:
- Tanto street como neighborhoods buscan en los 3 campos TEXT: address, neighborhood, title
- Se usa `Filter(should=[...3 MatchText...])` anidado dentro de `must`
- Esto garantiza que "Pueblo Cayaco" se encuentra sea que esté en address, neighborhood o title
- El LLM no necesita clasificar perfectamente: el sistema busca en todos los campos

### Qdrant: Configuración de colecciones
- **Una colección por modelo de embedding** (ej: `properties_openai_small`, `properties_openai_large`, `properties_gemini`)
- Cada colección tiene su vector dense con las dimensiones correspondientes
- **Payload indexes** (crear ANTES de subir datos):
  - `city` (keyword) — para filtrar por ciudad (normalizado)
  - `state` (keyword) — para filtrar por estado (normalizado)
  - `neighborhood` (text) — full-text index para partial matching (must, OR con address/title)
  - `address` (text, MULTILINGUAL) — para MatchText de calles (must, OR con neighborhood/title)
  - `title` (text, MULTILINGUAL) — para MatchText de keywords en título (must, OR con address/neighborhood)
  - `property_type` (keyword) — casa, departamento, terreno, etc.
  - `operation` (keyword) — sale, rent
  - `bedrooms` (integer) — número de recámaras
  - `bathrooms` (integer) — número de baños
  - `price` (float) — para rangos de precio
  - `surface` (float) — superficie total m²
  - `condition` (keyword) — Bueno, Excelente, etc.

### Escala 100K+
- **Scalar quantization INT8**: reduce RAM 4x con mínima pérdida de precisión
- **on_disk_payload**: payload en disco, vectores en RAM
- **Sharding**: NO necesario hasta 5M+ vectores

### Query parsing con Gemini 3 Flash
Usar structured output para extraer filtros del query.

**ParsedQuery soporta multi-valor**:
- `cities: list[str]` — múltiples ciudades ("gdl, zapopan, tlajo")
- `neighborhoods: list[str]` — múltiples colonias ("andares, puerta de hierro")
- `property_types: list[str]` — múltiples tipos ("bodega o nave")
- `street: str | None` — calle detectada ("calle alfonso nápoles")

El LLM parser extrae listas cuando el usuario menciona múltiples valores separados por comas, "y", "o".
El diccionario estático resuelve cada ciudad individualmente y las une en un solo MatchAny.

### Sparse vectors (BM25): Fase 5
Los sparse vectors ayudan con keywords exactos que dense vectors pierden
("roof garden", "jacuzzi", "doble altura", IDs internos).
Pero con filtros de metadata + dense vectors, el beneficio es marginal para el MVP.
Qdrant soporta BM25 server-side (modelo `Qdrant/bm25`, cero costo de API).
Se puede agregar como named vector a colecciones existentes + RRF fusion en Fase 5.

### Reranking: NO por ahora
Con filtros estructurados + dense search, es suficiente para el MVP.
Si se necesita en el futuro: Cohere Rerank 3.5 o BGE-reranker-v2-m3.

---

## Fases del proyecto

1. **Fase 1 — Backend base** ✅: Proyecto uv, FastAPI, modelos Pydantic, embedding providers, Qdrant manager
2. **Fase 2 — Ingesta** ✅: Excel loader, location normalizer, indexer, endpoint POST /ingest (8,803 propiedades)
3. **Fase 3 — Búsqueda** ✅: LLM query parsing multi-valor + filtros unified must + MatchText en address/title + desambiguación automática
4. **Fase 4 — Frontend playground** ✅: React 19 + Vite + Shadcn/ui con analytics y desambiguación clickeable
5. **Fase 4.5 — Chat conversacional** ✅: Agente LangGraph ReAct + Gemini 3 Flash + SSE streaming + UI split-screen
6. **Fase 5 — Mejoras**: Sparse vectors BM25 + RRF fusion, reranking, paginación, quantization
7. **Fase 6 — Deploy** ✅: Railway (backend) + Vercel (frontend) + Qdrant Cloud

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Health check del servidor |
| GET | `/health/qdrant` | Estado de las colecciones en Qdrant |
| GET | `/models` | Lista de modelos de embedding soportados |
| POST | `/ingest` | Indexar propiedades del Excel en Qdrant |
| POST | `/search` | Búsqueda single-shot en lenguaje natural (Playground) |
| POST | `/chat` | Chat conversacional via SSE streaming |
| GET | `/chat/{id}/history` | Historial de una sesión de chat |
| DELETE | `/chat/{id}` | Borrar sesión de chat |
| GET | `/docs` | Swagger UI |

---

## Variables de entorno

```bash
# .env (basado en .env.example)
GEMINI_API_KEY=AI...              # Requerido (embeddings, query parser, agente)
OPENAI_API_KEY=sk-...             # Opcional (solo si usas modelos OpenAI)
DEFAULT_EMBEDDING_MODEL=gemini    # gemini | openai-small | openai-large

# Agente conversacional
AGENT_MODEL=gemini-3-flash-preview

# Qdrant local (desarrollo)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Qdrant Cloud (producción — si se configura, ignora host/port)
QDRANT_URL=https://xxx.cloud.qdrant.io:6333
QDRANT_API_KEY=tu-api-key

CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

---

## Comandos útiles

```bash
# Levantar Qdrant local
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant:latest

# Entrar al backend
cd backend

# Sincronizar dependencias
uv sync

# Activar entorno
source .venv/bin/activate

# Instalar nueva dependencia
uv add <paquete>

# Correr backend
uvicorn main:app --reload

# Indexar propiedades (con el backend corriendo)
curl -X POST "http://localhost:8000/ingest?model=gemini"
curl -X POST "http://localhost:8000/ingest?all_models=true"

# Verificar indexación
curl http://localhost:8000/health/qdrant

# Probar chat (SSE streaming)
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "terreno en el centro", "model": "gemini"}'

# Frontend
cd frontend && npm install && npm run dev  # http://localhost:5173
```
