# API Reference

## Bridge

The main class for connecting to MariaDB and performing vector operations.
```python
from mdbrag import Bridge
```

---

### `Bridge.__init__(connection_string)`

Initializes the Bridge and validates the MariaDB version.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `connection_string` | `str` | SQLAlchemy-compatible MariaDB URI |

**Connection string format:**
```
mariadb+pymysql://user:password@host:port/database
```

**Raises:**

| Exception | When |
|---|---|
| `ValueError` | Connection string is not a MariaDB URI |
| `VersionError` | MariaDB version is below 11.8 |
| `ConnectionError` | Cannot connect to the database |

**Example:**
```python
bridge = Bridge("mariadb+pymysql://user:pass@localhost:3306/mydb")
```

---

### `Bridge.vectorize(source_table, fields, vectors)`

Creates a vector table from an existing table using pre-computed embeddings.
The original table is never modified.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `source_table` | `str` | Name of the existing table to vectorize |
| `fields` | `list[str]` | Column names to include in the vector table |
| `vectors` | `list[list[float]]` | Pre-computed embeddings, one per row |

**Returns:** `dict`
```python
{
    "table_name": "clientes_vectors",  # always {source_table}_vectors
    "row_count": 100,
    "vector_dim": 1536
}
```

**Raises:**

| Exception | When |
|---|---|
| `TableNotFoundError` | `source_table` does not exist |
| `ColumnNotFoundError` | Any field in `fields` does not exist |
| `VectorizationError` | `vectors` is empty or length doesn't match row count |

**Notes:**
- If `{source_table}_vectors` already exists, it will be overwritten.
- `len(vectors)` must equal the number of rows in `source_table`.
- All vectors must have the same dimension.

**Example:**
```python
result = bridge.vectorize(
    source_table="clientes",
    fields=["notas", "descripcion"],
    vectors=my_embeddings
)
```

---

### `Bridge.search(query_vector, table_name, top_k)`

Performs semantic search on a vector table using cosine distance.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query_vector` | `list[float]` | required | Pre-computed query embedding |
| `table_name` | `str` | required | Name of the vector table to search |
| `top_k` | `int` | `5` | Number of results to return |

**Returns:** `list[dict]`
```python
[
    {
        "original_id": 42,
        "combined_text": "cliente con problema de facturación",
        "similarity": 0.97,
        "rank": 1
    },
    ...
]
```

**Raises:**

| Exception | When |
|---|---|
| `NoVectorTableError` | `table_name` does not exist |

**Notes:**
- `similarity` is `1 - cosine_distance`. Higher is more similar.
- `query_vector` must have the same dimension as the stored vectors.
- Results are ordered by similarity descending.

**Example:**
```python
results = bridge.search(
    query_vector=query_embedding,
    table_name="clientes_vectors",
    top_k=10
)
```

---

## Exceptions

All exceptions inherit from `MdbRagError`.
```python
from mdbrag.exceptions import (
    MdbRagError,        # base exception
    ConnectionError,    # database connection failed
    VersionError,       # MariaDB version below 11.8
    TableNotFoundError, # source table does not exist
    ColumnNotFoundError,# specified column does not exist
    NoVectorTableError, # vector table does not exist
    VectorizationError, # vectorization operation failed
)
```