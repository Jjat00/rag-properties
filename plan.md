# RAG Properties — Plan del Proyecto

## Decisiones de arquitectura (investigadas y validadas)

### Embedding: Qué texto embeddear

**Template** (Title primero por mayor valor semántico):
```
{Title}. {Type} en {operation} en {Neighborhood}, {City}, {State}.
{Bedrooms} recámaras, {Bathrooms} baños, {Surface}m².
Condición: {Condition}.
```

| Decisión | Resultado | Razón |
|----------|-----------|-------|
| Title en embedding | **Sí, primero** | Mayor valor semántico; matchea queries descriptivos |
| Campos numéricos (recámaras, baños, superficie) | **Sí, como fallback** | Si el LLM parser falla en extraer, el vector lo atrapa |
| Precio en embedding | **No** | Filtro exacto/rango es estrictamente mejor que semántica para números |
| Dirección cruda en embedding | **No** | Ruido puro ("Av. 5, C. 19 Región 012..."); usuario no busca así |
| Neighborhood en embedding | **Sí** | Usuarios buscan por zona/colonia de forma descriptiva |
| Datos del agente | **No** | Irrelevante para búsqueda de propiedades |

### Vectores: Uno solo por propiedad

| Opción | Veredicto | Razón |
|--------|-----------|-------|
| Single vector | **Elegido** | Filtros de metadata ya separan por aspecto |
| Named vectors (location + description) | Descartado | Ubicación y descripción están correlacionados; filtros ya manejan la separación |
| Multiple dense vectors | Descartado | 3x costo de embedding, complejidad innecesaria |

Aplica para 8K y 100K+. Named vectors solo se justificarían para modalidades distintas (imagen + texto).

### Colecciones: Una por modelo de embedding

3 colecciones para A/B testing:
- `properties_openai_small` (1536d)
- `properties_openai_large` (3072d)
- `properties_gemini` (3072d) — **default**

Después de determinar ganador → consolidar a 1 colección.

### Query: Embeddear query completo del usuario

**Siempre el query completo**, no el residuo semántico post-filtros.
- El embedding de la propiedad incluye tipo y ubicación → el query debe alinearse
- Los filtros ya restringen candidatos → redundancia no daña
- Implementación más simple

### Normalización de ubicaciones mexicanas

**Problema**: Qdrant keyword filters son exact-match. "Edomex" ≠ "Estado de México".

**Solución: Doble capa**

1. **Diccionario estático** (`location_normalizer.py`):
   - Ingesta: canonicalizar datos del Excel antes de indexar
   - Query: normalizar input del usuario antes de filtrar
   - Cubre: CDMX/DF, Edomex, Q.Roo, acentos, abreviaciones comunes
   - Costo: cero

2. **LLM parser** (Gemini 3 Flash):
   - Resuelve ambigüedades ("México" solo → contexto)
   - Normaliza variantes no cubiertas por diccionario
   - Recibe lista de nombres canónicos en el system prompt

**Gotchas específicos**:
- Municipio vs ciudad (Benito Juárez vs Cancún) → `MatchAny` con variantes
- Colonias sin estándar → NO keyword filter, solo embedding semántico
- `neighborhood` indexado como TEXT (full-text), no KEYWORD

### Sparse vectors (BM25): Fase 5

| Factor | Sin sparse | Con sparse (BM25 + RRF) |
|--------|-----------|------------------------|
| Complejidad | Baja | Media |
| Costo | Solo dense API | Dense API + BM25 gratis (Qdrant server-side) |
| Keywords exactos ("roof garden", "jacuzzi") | Depende del dense | Match directo |
| Con filtros ya aplicados | Bueno | Marginalmente mejor |

Qdrant hace BM25 internamente (`Qdrant/bm25`) → solo configuración, no API externa.
Se agrega como named vector a colecciones existentes + RRF fusion.

### Escala 100K+

- **Scalar quantization INT8**: `ScalarQuantization(INT8, quantile=0.99, always_ram=True)` → 4x menos RAM
- **on_disk_payload**: payload en disco, vectores en RAM
- **HNSW defaults**: suficientes hasta 100K; Qdrant auto-switch a brute-force cuando filtros reducen <1000 candidatos
- **Sharding**: NO necesario hasta 5M+

---

## Agente Conversacional (Fase 4.5)

### Por qué LangGraph ahora

CLAUDE.md original decía "no LangGraph" porque el flujo de búsqueda era lineal (query → parse → search).
**El chat conversacional SÍ justifica LangGraph**: loop tool-calling, memoria multi-turno, streaming.
El endpoint `/search` (playground) sigue siendo FastAPI puro, sin LangGraph.

### Arquitectura del agente

```
┌─ POST /chat (SSE) ──────────────────────────────────┐
│                                                      │
│  User message                                        │
│       ↓                                              │
│  ┌──────────────┐   tool_calls?   ┌───────────────┐  │
│  │  agent_node   │ ────────────→  │  tool_node    │  │
│  │ (Gemini 3     │ ←────────────  │ (search_      │  │
│  │  Flash +      │  tool results  │  properties)  │  │
│  │  tools bound) │                └───────────────┘  │
│  └──────────────┘                                    │
│       ↓ no tool_calls                                │
│  Respuesta texto (streaming SSE token por token)     │
│       ↓                                              │
│  Frontend: chat panel (60%) + properties panel (40%) │
└──────────────────────────────────────────────────────┘
```

### Modelos LLM usados

| Uso | Modelo | Provider | Configuración |
|-----|--------|----------|---------------|
| Embeddings (default) | `gemini-embedding-001` | Google Gemini | 3072d, cosine |
| Query parsing | `gemini-3-flash-preview` | Google Gemini | temp=0, structured output |
| Agente conversacional | `gemini-3-flash-preview` | Google Gemini | temp=0.3, tool calling |

### Decisiones del agente

| Decisión | Elección | Razón |
|----------|----------|-------|
| Framework | LangGraph (ReAct) | Loop tool-calling nativo, checkpointer, streaming |
| LLM | Gemini 3 Flash | Consistencia con stack, tool calling robusto |
| Streaming | SSE (sse-starlette) | Token por token como ChatGPT |
| Memoria | MemorySaver (in-memory) | Checkpointer built-in, sin DB extra |
| Query passthrough | Verbatim | El agente pasa el query del usuario EXACTO al tool; el QueryParser interpreta |

### Regla clave del prompt

**El agente NUNCA reformula el query del usuario.** Lo pasa tal cual a `search_properties`.
El QueryParser downstream tiene toda la inteligencia para interpretar:
- Calles mexicanas (Illinois, Masaryk, Alfonso Nápoles)
- Colonias (Andares, Puerta de Hierro, Valle Real)
- Múltiples ubicaciones ("gdl, zapopan, tlajo")
- Abreviaciones y errores ortográficos

Si el agente reformula, pierde información que el parser sí entiende.

### SSE Events

| Evento | Data | Frontend |
|--------|------|----------|
| `session` | `{session_id}` | Guardar ID para continuidad |
| `token` | string | Agregar al bubble del assistant |
| `tool_start` | `{name, args}` | Mostrar "Buscando..." |
| `results` | `PropertyResult[]` | Actualizar panel de propiedades |
| `filters` | `ParsedQuery` | Mostrar chips de filtros |
| `disambiguation` | `DisambiguationInfo[]` | Mostrar badges de desambiguación |
| `state_results` | `{estado: PropertyResult[]}` | Pre-fetched por estado |
| `metrics` | `SearchMetrics` | Panel debug (colapsable) |
| `done` | `""` | Habilitar input |
| `error` | string | Mostrar error |

### Frontend Chat

- **Layout**: Split-screen 60% chat / 40% propiedades (desktop). Stacked en mobile.
- **Chat panel**: Lista de mensajes scrollable + textarea con Enter-to-send
- **Message bubbles**: User (derecha, azul) / Assistant (izquierda, gris) con markdown rendering
- **Properties panel**: FilterChips + PropertyCards (reutiliza componentes existentes) + debug colapsable
- **Toggle**: Chat / Playground en la navbar. Chat es la vista default.

### Dependencias agregadas (Fase 4.5)

**Backend** (via `uv add`):
- `langchain-core` — Abstracciones de mensajes y tools
- `langgraph` — StateGraph, MemorySaver, ReAct loop
- `langchain-google-genai` — ChatGoogleGenerativeAI con tool calling
- `sse-starlette` — EventSourceResponse para SSE streaming

**Frontend** (via `npm install`):
- `react-markdown` — Renderizar markdown en burbujas del assistant

---

## Estrategia de búsqueda: unified must + semántica

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
    → Retorna top-k propiedades + state_results pre-fetched
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

### Query parsing con Gemini 3 Flash

Structured output JSON para extraer filtros del query.

**ParsedQuery soporta multi-valor**:
- `cities: list[str]` — múltiples ciudades ("gdl, zapopan, tlajo")
- `neighborhoods: list[str]` — múltiples colonias ("andares, puerta de hierro")
- `property_types: list[str]` — múltiples tipos ("bodega o nave")
- `street: str | None` — calle detectada ("calle alfonso nápoles")

El LLM parser extrae listas cuando el usuario menciona múltiples valores separados por comas, "y", "o".
El diccionario estático resuelve cada ciudad individualmente y las une en un solo MatchAny.

### Reranking: NO por ahora
Con filtros estructurados + dense search, es suficiente para el MVP.
Si se necesita en el futuro: Cohere Rerank 3.5 o BGE-reranker-v2-m3.

---

## Fases de implementación

### Fase 1 — Backend base ✅
- [x] Inicializar proyecto con uv en `backend/`
- [x] Config con EmbeddingModel enum y Settings
- [x] Modelo Property con validators y embedding_text
- [x] Embedding providers: OpenAI, Gemini, Registry
- [x] QdrantManager con colecciones e indexes
- [x] FastAPI app con /health, /health/qdrant, /models

### Fase 2 — Ingesta ✅
- [x] Auditar Excel: 8808 filas, 8803 IDs únicos, states inconsistentes identificados
- [x] `ingestion/location_normalizer.py`: STATE_CANONICAL (ingesta) + STATE_ALIASES (query-time)
- [x] `ingestion/excel_loader.py`: leer Excel → lista de Property (con canonicalización, NaN→None, dedup)
- [x] `ingestion/indexer.py`: generar embeddings en batches → upsert en Qdrant (UUID5 determinísticos)
- [x] `neighborhood` index de KEYWORD a TEXT (multilingual tokenizer) en qdrant_manager
- [x] `upsert_points()` con batches de 100 en qdrant_manager
- [x] Endpoint POST `/ingest` con params `model` y `all_models`
- [x] Fix `property.py`: id: str (no int), coerce_to_str para phone/id, embedding_text sin precio
- [x] Fix `gemini_provider.py`: sync→asyncio.to_thread(), modelo actualizado a gemini-embedding-001 (3072d)
- [x] Verificado: 8803 propiedades cargadas, states canonicalizados correctamente

### Fase 3 — Búsqueda ✅
- [x] `search/query_parser.py`: Gemini 3 Flash con structured output → ParsedQuery
- [x] LLM prompt basado en datos reales del catálogo: 27 estados, 32 municipios, 80 colonias top, calles frecuentes
- [x] Reglas de extracción: calle vs colonia basado en lista de colonias del catálogo
- [x] `search/searcher.py`: filtros unified must + vector search con query completo
- [x] Multi-valor: cities[], neighborhoods[], property_types[] con MatchAny por unión de aliases
- [x] Texto unificado: street y neighborhoods buscan en 3 campos TEXT con OR anidado
- [x] TEXT indexes en address y title (MULTILINGUAL tokenizer)
- [x] Desambiguación automática: facet por estado, conteo por colonia, count() por tipo
- [x] `state_results: dict[str, list[PropertyResult]]` — pre-fetched por estado
- [x] Endpoint POST `/search`

### Fase 4 — Frontend Playground ✅
- [x] Playground web: React 19 + Vite 7 + Shadcn/ui + Tailwind v4 (dark theme)
- [x] Barra de búsqueda con selección de modelo y top_k
- [x] Cards de propiedades con precio, ubicación, atributos y score
- [x] Gráfica de similitud interactiva (Recharts + d3-force)
- [x] Analytics: distribución de scores, histograma, métricas
- [x] Desambiguación clickeable: badges por estado, tipo y colonia

### Fase 4.5 — Chat Conversacional ✅
- [x] Backend: módulo `agent/` con LangGraph ReAct (state, prompt, tools, graph, session)
- [x] Tool `search_properties` que wrappea el pipeline de búsqueda existente
- [x] Agente Gemini 3 Flash con tool calling y memoria in-memory (MemorySaver)
- [x] Endpoint POST `/chat` con SSE streaming (token, results, filters, disambiguation, metrics)
- [x] Endpoint GET `/chat/{id}/history` y DELETE `/chat/{id}`
- [x] Frontend: vista Chat con split-screen (60% chat, 40% propiedades)
- [x] SSE stream parser con callbacks tipados (`chat-api.ts`)
- [x] Hook `useChat` para estado del chat + streaming
- [x] Componentes: ChatInput, ChatMessage (con markdown), ChatPanel, PropertiesPanel, ChatView
- [x] Toggle Chat/Playground en navbar
- [x] Fix: Gemini devuelve content como lista de partes (no string) → extracción correcta
- [x] Fix: Agent prompt reforzado para pasar query verbatim al tool (no reformular)
- [x] Default embedding model cambiado a `gemini`

### Fase 5 — Mejoras (pendiente)
- [ ] Sparse vectors BM25 + RRF hybrid search
- [ ] Reranking (Cohere Rerank 3.5 si se necesita)
- [ ] Paginación de resultados
- [ ] Scalar quantization INT8 para escala

### Fase 6 — Deploy ✅
- [x] Soporte Qdrant Cloud: `QDRANT_URL` + `QDRANT_API_KEY` en config y QdrantManager
- [x] Backend en Railway (FastAPI + uv)
- [x] Frontend en Vercel (React + Vite)
- [x] Re-indexar 8803 propiedades en Qdrant Cloud
