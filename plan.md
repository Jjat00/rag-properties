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
- `properties_gemini` (3072d)

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

2. **LLM parser** (Gemini Flash):
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
- [x] `search/query_parser.py`: Gemini Flash con structured output → ParsedQuery (city, state, type, bedrooms, bathrooms, price_min, price_max, operation, semantic_query)
- [x] `search/searcher.py`: construir filtros Qdrant + vector search con query completo del usuario
- [x] Endpoint POST `/search` con query en lenguaje natural, modelo y top_k
- [x] SearchMetrics en respuesta: scores de similitud, filtros aplicados, tiempo de respuesta
- [x] Query parser actualizado a `gemini-2.0-flash-preview` (gemini-3-flash-preview)

### Fase 4 — Frontend ✅
- [x] Playground web: React 19 + Vite 7 + Shadcn/ui + Tailwind v4 (dark theme)
- [x] Barra de búsqueda con selección de modelo y top_k
- [x] Cards de propiedades con precio, ubicación, atributos y score de similitud
- [x] Loading skeleton mientras carga
- [x] Gráfica de similitud interactiva (Recharts + d3-force) — scatterplot con zoom/pan
- [x] Analytics: distribución de scores, histograma, métricas de búsqueda
- [x] Manejo de errores y estados vacíos

### Fase 5 — Mejoras (pendiente)
- [ ] Sparse vectors BM25 + RRF hybrid search
- [ ] Reranking (Cohere Rerank 3.5 si se necesita)
- [ ] Paginación de resultados
- [ ] Scalar quantization INT8 para escala

### Fase 6 — Deploy (en progreso)
- [x] Soporte Qdrant Cloud: `QDRANT_URL` + `QDRANT_API_KEY` en config y QdrantManager
- [ ] Backend en Railway (FastAPI + uv)
- [ ] Frontend en Vercel (React + Vite)
- [ ] Re-indexar 8803 propiedades en Qdrant Cloud
