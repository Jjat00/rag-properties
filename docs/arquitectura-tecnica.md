# Arquitectura Técnica — RAG Properties

Sistema de búsqueda semántica de propiedades inmobiliarias en México.
8,803 propiedades, búsqueda en lenguaje natural, filtros estructurados + vector search.

---

## 1. Flujo general

```
Query del usuario
    │
    ▼
[1] LLM Parser (Gemini Flash)
    → Extrae filtros estructurados: ciudad, tipo, recámaras, precio, etc.
    → Mantiene el query completo como semantic_query
    │
    ▼
[2] Normalización de ubicaciones (diccionario estático)
    → "Cancún" → ["Cancún", "Benito Juárez"]
    → "CDMX" → [16 delegaciones]
    │
    ▼
[3] Pre-filtro en Qdrant (metadata filters)
    → Reduce de 8,803 a un subconjunto pequeño y exacto
    │
    ▼
[4] Búsqueda vectorial (cosine similarity)
    → El query completo se embeddea contra las propiedades filtradas
    │
    ▼
[5] Top-K resultados ordenados por relevancia semántica
```

---

## 2. Curación y carga de datos

### Fuente
Excel con 8,808 filas y 21 columnas. Tras deduplicar por ID: **8,803 propiedades únicas**.

### Problemas encontrados y cómo se resolvieron

| Problema | Solución |
|----------|----------|
| 5 IDs duplicados | `drop_duplicates(subset="id", keep="first")` |
| `agent_phone` viene como float/int de pandas | validator `coerce_to_str`: convierte a string antes de validar |
| IDs hexadecimales tratados como números por Excel | mismo validator `coerce_to_str` |
| Precios en formato mexicano: `"30.000.000"` o `"139,5"` | `_normalize_number()`: regex detecta formato MX y convierte |
| Valores NaN de pandas en campos opcionales | `_clean_value()`: convierte `float('nan')`, `pd.NaT` y `None` → `None` |
| Estados con nombres inconsistentes en el Excel | `STATE_CANONICAL`: "Estado de México" → "Edo. de México", "Baja California Norte" → "Baja California", "San luis Potosí" → "San Luis Potosí" |
| Columnas del Excel con nombres verbosos | `EXCEL_COLUMN_MAP`: renombra "Attributes: Suites" → `bedrooms`, etc. |

### Pipeline de carga (`excel_loader.py`)
1. `pd.read_excel()` → DataFrame
2. Renombrar columnas con `EXCEL_COLUMN_MAP`
3. Deduplicar por `id`
4. Por cada fila: `_clean_value()` → `canonicalize_state()` → `canonicalize_city()` → `Property(**row_dict)`
5. Validación Pydantic con field validators por tipo de campo

---

## 3. Modelo de datos (`Property`)

Todos los campos son `Optional` — el Excel tiene muchos nulls y no se rechaza ninguna propiedad por campos faltantes.

### Validators por tipo
- **`agent_phone`, `id`, `internal_id`**: `coerce_to_str` — pandas puede leerlos como int/float
- **`price`, `surface`, `roofed_surface`**: `normalize_numeric` — maneja formatos numéricos MX
- **`bedrooms`, `bathrooms`**: `normalize_int_like` — convierte a float y trunca decimales (no existen 2.5 recámaras)

---

## 4. Qué se embeddea (y qué no)

### Template de embedding (`embedding_text`)

```
{Title}. {Type} en {operation} en {Neighborhood}, {City}, {State}.
{Bedrooms} recámaras, {Bathrooms} baños, {Surface}m². Condición: {Condition}.
```

Los fragmentos con valores `None` se omiten completamente — nunca se embeddea "None" o "N/A".

### Decisiones campo por campo

| Campo | ¿En embedding? | Razón |
|-------|---------------|-------|
| **Title** | ✅ Primero | Texto escrito por humanos, mayor valor semántico. Matchea queries descriptivos como "amplia con jardín y vista al mar" |
| **Type** (tipo) | ✅ | "Casa", "Departamento", "PH" — vocabulario que el usuario usa |
| **Operation** (venta/renta) | ✅ | El usuario lo menciona en el query |
| **Neighborhood** (colonia) | ✅ | Los usuarios buscan por zona de forma descriptiva ("Polanco", "Roma Norte") |
| **City** | ✅ | Contexto geográfico esencial |
| **State** | ✅ | Desambigua ciudades con mismo nombre en distintos estados |
| **Bedrooms/Bathrooms** | ✅ Como fallback | Si el LLM parser falla en extraer el número, el vector lo atrapa |
| **Surface** | ✅ Como fallback | Idem |
| **Condition** | ✅ | "Excelente", "Para remodelar" son descriptores que el usuario puede mencionar |
| **Price** | ❌ | Un filtro de rango exacto es estrictamente mejor que similitud semántica para números |
| **Address** (calle) | ❌ | "Av. 5, C. 19 Colonia Tumben Kaa norte-Región 012" es ruido puro. Los usuarios no buscan por calle exacta |
| **Agent data** | ❌ | Irrelevante para la búsqueda de propiedades |

### Por qué un solo vector por propiedad
Los filtros de metadata ya separan por aspecto (ciudad, tipo, recámaras). Named vectors
(ej. "location vector" + "description vector") añadirían 3x costo de embedding sin beneficio:
ubicación y descripción están correlacionados semánticamente y los filtros ya los manejan.

### Por qué embeddear el query completo
El embedding de la propiedad incluye tipo y ubicación. Si se embeddeara solo el "residuo semántico"
post-filtros, se perdería alineación con el vector de la propiedad. Los filtros ya reducen los
candidatos — la redundancia en el vector no daña.

---

## 5. Modelos de embedding

| Modelo | Dimensiones | Colección Qdrant | Costo |
|--------|------------|------------------|-------|
| `text-embedding-3-small` | 1536d | `properties_openai_small` | $0.02/M tokens |
| `text-embedding-3-large` | 3072d | `properties_openai_large` | $0.13/M tokens |
| `gemini-embedding-001` | 3072d | `properties_gemini` | $0.15/M tokens |

**Una colección por modelo** para A/B testing limpio. Qdrant requiere dimensiones uniformes
por colección. El modelo activo se configura via env var `DEFAULT_EMBEDDING_MODEL`.

**Similitud**: Cosine en todos los modelos — invariante a la magnitud del vector,
adecuado para comparar semántica de texto.

---

## 6. Indexación en Qdrant

### IDs: hex → UUID5 determinístico
Los IDs del Excel son hex strings (`68f2e999d0e6dd4c13fe9da9`). Qdrant requiere UUID.
Se usa `uuid.uuid5(namespace, hex_id)` con namespace fijo — mismo ID siempre produce
el mismo UUID. Esto hace los upserts idempotentes: re-indexar no duplica datos.

### Payload indexes (creados antes de subir datos)

| Campo | Tipo de índice | Uso |
|-------|---------------|-----|
| `city` | KEYWORD | Exact match tras normalización |
| `state` | KEYWORD | Exact match tras normalización |
| `neighborhood` | TEXT (multilingual tokenizer, min 2 chars) | Partial matching para colonias |
| `property_type` | KEYWORD | Exact match con MatchAny para subtipos |
| `operation` | KEYWORD | "sale" / "rent" |
| `bedrooms` | INTEGER | Rangos `gte`/`lte` |
| `bathrooms` | INTEGER | Rangos `gte`/`lte` |
| `price` | FLOAT | Rangos de precio |
| `surface` | FLOAT | Rangos de superficie |
| `condition` | KEYWORD | Estado de la propiedad |
| `currency` | KEYWORD | "MXN" / "USD" |

**Por qué `neighborhood` es TEXT y no KEYWORD**: Las colonias no tienen nombres estandarizados.
"Lomas de Vista Hermosa" vs "Lomas de Vista Hermosa Norte" vs "Lomas de Chapultepec".
Un full-text index con tokenización multilingual permite matching parcial. Además, en búsqueda
no se filtra por neighborhood con keyword (demasiado estricto) — se deja al embedding.

### Batches de upsert
Los 8,803 puntos se suben en batches de 100. Qdrant tiene límites de payload por request;
los batches evitan timeouts y permiten logging de progreso cada 1,000 puntos.

---

## 7. Normalización de ubicaciones (doble capa)

### El problema
Los filtros keyword de Qdrant son exact-match. "Edomex" ≠ "Edo. de México".
Si la normalización falla, el filtro no encuentra nada y el vector search devuelve
resultados de todo el catálogo — ignorando la intención geográfica del usuario.

### Capa 1 — Diccionario estático (costo cero)

**En ingesta** (`STATE_CANONICAL`): Corrige inconsistencias en el propio Excel.
Auditado con `df["Address: State: Name"].value_counts()` para identificar variantes.

**En query time** (`STATE_ALIASES`, `CITY_ALIASES`): Normaliza el input del usuario.

```python
# Ejemplos STATE_ALIASES
"edomex" → "Edo. de México"
"cdmx"   → "Ciudad de México"
"df"     → "Ciudad de México"
"q. roo" → "Quintana Roo"
"nl"     → "Nuevo León"

# Ejemplos CITY_ALIASES (MatchAny — múltiples valores)
"cancún" → ["Cancún", "Benito Juárez"]          # municipio vs coloquial
"cdmx"   → [16 delegaciones]                    # usuario dice ciudad, datos tienen delegación
"gdl"    → ["Guadalajara", "Zapopan", "Tlajomulco de Zúñiga"]
"mty"    → ["Monterrey", "San Pedro Garza García", "San Nicolás de los Garza"]
```

### El truco de MatchAny para ciudades
El catálogo usa nombres de **municipio** (`Benito Juárez`, `Solidaridad`, `Miguel Hidalgo`)
en lugar del nombre coloquial (`Cancún`, `Playa del Carmen`, `Polanco`).
La solución: cuando el usuario dice "Cancún", buscar con
`MatchAny(any=["Cancún", "Benito Juárez"])` — cubre ambos formatos sin que el usuario
sepa de la distinción municipio/ciudad.

### Capa 2 — LLM parser
Gemini Flash resuelve variantes no cubiertas por el diccionario y ambigüedades
contextuales ("México" solo → Ciudad de México vs Estado de México según contexto).
Recibe la lista de estados canónicos en el system prompt.

### Por qué neighborhood NO tiene filtro keyword
Las colonias no tienen estándar y los usuarios mezclan colonias, landmarks, zonas y
referencias informales ("cerca del Parque Lincoln", "zona Rosa"). Un filtro keyword
fallaría casi siempre. Se deja al embedding semántico que lo maneja con mayor tolerancia.

---

## 8. LLM Query Parser

### Modelo
`gemini-2.0-flash` (flash-preview) con structured output (`response_mime_type="application/json"`
+ `response_json_schema`). Temperature 0 para máxima consistencia en extracción.

### Schema extraído (`ParsedQuery`)

```python
city: str | None
state: str | None
neighborhood: str | None       # informativo, no se filtra con keyword
property_type: str | None
operation: str | None          # "sale" | "rent"
min_bedrooms: int | None
max_bedrooms: int | None
min_bathrooms: int | None
max_bathrooms: int | None
min_price: float | None
max_price: float | None
min_surface: float | None
max_surface: float | None
condition: str | None
currency: str | None           # "MXN" | "USD"
semantic_query: str            # query completo original, siempre presente
```

### System prompt — decisiones de diseño

**Tipos de propiedad genéricos**: El LLM extrae tipos genéricos ("Terreno", "Casa", "PH").
El searcher expande automáticamente a subtipos via `PROPERTY_TYPE_ALIASES`.
Así el LLM no necesita conocer "Terreno residencial" vs "Terreno comercial".

**Conversión de precios**:
- `"4 millones"` / `"4M"` / `"4 mdp"` → `4000000`
- `"500 mil"` / `"500K"` → `500000`
- `"medio millón"` → `500000`

**Reglas de dirección para precios**:
- `"hasta X"` / `"menos de X"` / `"máximo X"` → solo `max_price`
- `"desde X"` / `"más de X"` / `"mínimo X"` → solo `min_price`
- `"de X"` / `"a X"` / `"30M"` sin calificador → rango ±5%: `min=X*0.95`, `max=X*1.05`
- `"más o menos X"` / `"aproximadamente X"` → rango ±5%

**Reglas para recámaras**: `"3 recámaras"` sin calificador → `min_bedrooms=3` (asume "al menos 3").
Diferente a precios porque en inmobiliario "3 recámaras" significa "de 3 en adelante",
mientras que un precio puntual como "30M" significa "alrededor de 30M".

**Fallback**: Si el LLM falla por cualquier razón (timeout, quota, error de parsing),
se retorna `ParsedQuery(semantic_query=query)` — búsqueda vectorial pura sin filtros.
El sistema nunca rompe por un fallo del parser.

---

## 9. Construcción de filtros Qdrant

### Expansión de tipos de propiedad (`PROPERTY_TYPE_ALIASES`)
El catálogo tiene subtipos granulares que el usuario no conoce:

```python
"Terreno" → MatchAny(["Terreno residencial", "Terreno comercial", "Terreno industrial"])
"Casa"    → MatchAny(["Casa", "Casa en condominio", "Casa uso de suelo"])
"Bodega"  → MatchAny(["Bodega comercial", "Nave industrial"])
"PH"      → MatchAny(["PH"])    # el LLM puede decir "PH", "Penthouse", "Pent house"
```

### Expansión de condiciones (`CONDITION_ALIASES`)
```python
"Nuevo" / "Nueva" → MatchAny(["Excelente"])   # el LLM puede inferir "nueva" = "Excelente"
```

### Filtros numéricos (Range)
Todos usan `gte`/`lte` (≥ / ≤). Los valores `None` simplemente se omiten del Range,
produciendo filtros unilaterales cuando aplica.

### Neighborhood: nunca como filtro keyword
Solo se filtra por: `city`, `state`, `property_type`, `operation`, `condition`, `currency`,
`bedrooms`, `bathrooms`, `price`, `surface`. La neighborhood se deja al vector search.

### Todos los filtros en `must` (AND)
Cada condición del array `must` debe cumplirse. No se usa `should` (OR) excepto dentro
de `MatchAny` para variantes del mismo campo.

---

## 10. Búsqueda vectorial

### Estrategia: filtros primero, semántica después
Qdrant aplica los filtros de metadata primero (operación O(log n) sobre índices invertidos),
luego hace vector search solo sobre el subconjunto filtrado. Con 8K propiedades y filtros
típicos (ciudad + tipo + recámaras) el subconjunto es de decenas a pocos cientos — el
vector search es casi instantáneo.

### HNSW (Hierarchical Navigable Small World)
Qdrant usa HNSW por defecto para approximate nearest neighbor. Con conjuntos pequeños
post-filtro (< 1,000 candidatos), Qdrant hace brute-force automáticamente — más exacto
y más rápido que HNSW para esos tamaños.

### Métricas devueltas en cada búsqueda
```
parse_time_ms         — tiempo del LLM parser
embed_time_ms         — tiempo de embedding del query
search_time_ms        — tiempo de Qdrant
total_time_ms         — tiempo total end-to-end
candidates_before_filter — total de puntos en la colección (8,803)
score_min / score_max / score_avg — distribución de similarity scores (0-1)
```

---

## 11. Payload almacenado en Qdrant

Todos los campos del Excel se guardan en el payload (excepto `embedding_text` que es transitorio).
El payload sirve para mostrar resultados en el frontend — no para el vector search.

```
id, title, property_type, operation, price, currency,
city, state, neighborhood, address, address_name,
bedrooms, bathrooms, surface, roofed_surface, condition,
internal_id, agent_first_name, agent_last_name, agent_company, agent_phone
```

Los campos de agente (nombre, empresa, teléfono) solo están en payload — nunca en el embedding.

---

## 12. Multi-modelo e intercambiabilidad

Tres colecciones paralelas permiten A/B testing sin tocar el código:
- La colección activa se selecciona por `model` en el request (`/search?model=gemini`)
- El `EmbeddingProvider` abstracto define la interfaz — cualquier proveedor implementa `embed_texts()` y `embed_query()`
- El `EmbeddingRegistry` cachea instancias por modelo (no se crean clientes nuevos por request)

---

## 13. Infraestructura de producción

| Componente | Servicio | Detalles |
|------------|----------|----------|
| Backend API | Railway | FastAPI + uvicorn, Python 3.12, uv para deps, Dockerfile en root del monorepo |
| Vector DB | Qdrant Cloud | 3 colecciones, ~8K puntos c/u, managed |
| Frontend | Vercel | React 19 + Vite 7 + Shadcn/ui, `vercel.json` proxy `/api/*` → Railway |
| Embeddings | OpenAI API + Gemini API | Solo APIs managed, nada self-hosted |
| Query parsing | Gemini API | Flash model para baja latencia |

### Proxy Vercel → Railway
El frontend usa rutas relativas (`/api/search`). Vercel reescribe server-side:
```json
{ "source": "/api/:path*", "destination": "https://rag-properties-production.up.railway.app/:path*" }
```
El browser nunca sabe la URL del backend. CORS configurado con `["*"]` en Railway
(y `allow_credentials=False` — necesario cuando `allow_origins=["*"]`).

---

## 14. Decisiones descartadas

| Idea | Por qué se descartó |
|------|---------------------|
| LangGraph | Flujo lineal sin branching ni loops. Un endpoint FastAPI simple es suficiente |
| Named vectors (location + description) | Correlacionados semánticamente; filtros ya separan por aspecto |
| Dirección cruda en embedding | Ruido puro ("Av. 5 C. 19 Región 012..."). El usuario no busca así |
| Filtro keyword en neighborhood | Nombres no estandarizados, demasiado estricto; el embedding lo maneja |
| Sparse BM25 (Fase 5) | Beneficio marginal con filtros + dense. Qdrant lo hace server-side con `Qdrant/bm25` sin costo de API, reservado para Fase 5 |
| Reranking (Cohere Rerank) | Con filtros estructurados + dense search es suficiente para el MVP |
| Self-hosting de modelos | Latencia y mantenimiento. Solo APIs managed |
| Múltiples vectores por propiedad | 3x costo, complejidad innecesaria para el volumen actual |
