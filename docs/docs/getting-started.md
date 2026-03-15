# Getting Started

## Requirements

- Python 3.9+
- MariaDB 11.8+ (self-hosted or PaaS)

**Supported deployment options:**

| Platform | Supported |
|---|---|
| Self-hosted (VPS, dedicated) | ✅ |
| Railway | ✅ |
| Render | ✅ |
| AWS RDS | ⏳ Rolling out 11.8 support |
| Google Cloud SQL | ⏳ Rolling out 11.8 support |

Cloud managed services are still rolling out MariaDB 11.8 support. 
This is a provider limitation, not a library limitation.

## Install
```bash
pip install mdb-rag
```

## Quickstart

**1. Connect to your MariaDB instance:**
```python
from mdbrag import Bridge

bridge = Bridge("mariadb+pymysql://user:pass@localhost:3306/mydb")
```

**2. Generate your embeddings externally:**

mdb-rag does not generate embeddings. Use any model you prefer:
```python
# Example with OpenAI
from openai import OpenAI

client = OpenAI()

rows = ["cliente con problema de facturación", "entrega tardía", "producto dañado"]

vectors = [
    client.embeddings.create(input=text, model="text-embedding-3-small")
    .data[0].embedding
    for text in rows
]
```

**3. Vectorize your table:**
```python
result = bridge.vectorize(
    source_table="clientes",
    fields=["notas", "descripcion"],
    vectors=vectors
)

print(result)
# {
#   "table_name": "clientes_vectors",
#   "row_count": 3,
#   "vector_dim": 1536
# }
```

**4. Search semantically:**
```python
# Generate query vector with the same model
query_vector = (
    client.embeddings.create(
        input="cliente con problema de facturación",
        model="text-embedding-3-small"
    )
    .data[0].embedding
)

results = bridge.search(
    query_vector=query_vector,
    table_name="clientes_vectors",
    top_k=5
)

for r in results:
    print(r["rank"], r["similarity"], r["combined_text"])
```

## What happens under the hood

When you call `vectorize()`, mdb-rag creates a new table 
`{source_table}_vectors` with a `VECTOR` column and an HNSW index. 
Your original table is never modified.

When you call `search()`, mdb-rag uses `VEC_DISTANCE_COSINE()` with 
the HNSW index to find the most semantically similar rows.