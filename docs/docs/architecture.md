# Architecture

## The bridge pattern

mdb-rag is built around a single idea: your data is already in MariaDB,
and it should stay there. The library does not move data, does not sync
to external services, and does not generate embeddings.

What it does is bridge two schemas inside the same database instance.
Your original table is never touched. mdb-rag creates a parallel vector
table and keeps the reference back to the original row via `original_id`.

**Your existing schema:**

| Column | Type |
|---|---|
| id | INT |
| notas | TEXT |
| descripcion | TEXT |
| created_at | DATETIME |

**mdb-rag vector schema (created automatically):**

| Column | Type |
|---|---|
| id | INT AUTO_INCREMENT |
| original_id | INT |
| combined_text | TEXT |
| embedding | VECTOR(1536) |

---

## How vectorize() works

1. mdb-rag reads all rows from `source_table`
2. Creates `{source_table}_vectors` with a `VECTOR` column and HNSW index
3. Inserts each row using `Vec_FromText()` to store the embedding
4. Returns `{ table_name, row_count, vector_dim }`

The SQL it runs internally:
```sql
CREATE TABLE clientes_vectors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    original_id INT,
    combined_text TEXT,
    embedding VECTOR(1536) NOT NULL,
    VECTOR INDEX idx_vector (embedding)
);

INSERT INTO clientes_vectors (original_id, combined_text, embedding)
VALUES (1, 'texto...', Vec_FromText('[0.1, 0.2, ...]'));
```

---

## How search() works

1. Validates that `table_name` exists
2. Runs cosine distance search using the HNSW index
3. Computes similarity as `1 - cosine_distance`
4. Returns results ranked by similarity descending

The SQL it runs internally:
```sql
SELECT original_id, combined_text,
       VEC_DISTANCE_COSINE(embedding, Vec_FromText('[...]')) as distance
FROM clientes_vectors
ORDER BY distance ASC
LIMIT 5;
```

---

## Why HNSW

MariaDB 11.8 implements a modified version of the HNSW algorithm
(Hierarchical Navigable Small World) for Approximate Nearest Neighbor search.

HNSW is what makes vector search fast at scale. Without it, every search
is a full table scan at O(n). With HNSW, search complexity drops to
approximately O(log n).

mdb-rag creates the HNSW index automatically when you call `vectorize()`.
You don't need to configure anything.

---

## Why cosine distance

mdb-rag uses `VEC_DISTANCE_COSINE()` for all searches. Cosine distance
measures the angle between two vectors, not their magnitude. This makes
it the right choice for text embeddings where direction matters more than
length.

The similarity score returned by `search()` is `1 - cosine_distance`,
so higher values mean more similar. A score of `1.0` is identical,
`0.0` is completely unrelated.

---

## Latency considerations

mdb-rag is not designed for sub-10ms vector search. If your use case
requires that, use Redis with RediSearch as your hot layer.

mdb-rag is designed for teams that need semantic search without adding
new infrastructure. The latency trade-off is intentional and documented.

| Layer | Latency | Use case |
|---|---|---|
| Redis + RediSearch | less than 10ms | Real-time inference, live search |
| mdb-rag + MariaDB 11.8 | 50-200ms | RAG pipelines, async search, analytics |
| External vector DB | varies | Large scale, multi-tenant |

If your RAG pipeline can absorb 50-200ms on the retrieval step,
mdb-rag gives you that capability with zero new infrastructure.