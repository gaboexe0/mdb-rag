# mdb-rag: RAG pipelines for teams already running MariaDB

70-80% of legacy data in LATAM lives in MySQL/MariaDB. This library lets you plug that data into a RAG pipeline without migrating your stack.

## The problem

Legacy MySQL/MariaDB data can't participate in AI pipelines without expensive ETL to PostgreSQL or external vector DBs. mdb-rag solves this with MariaDB 11.8 native HNSW vector indexes.

## Install

```bash
pip install mdb-rag
```

## Requirements

- MariaDB 11.8+, self-hosted or PaaS (Railway, Render)
- Major cloud managed services (AWS RDS, Google Cloud SQL) are still rolling out 11.8 support — this is a provider limitation, not a library limitation

## Quickstart

```python
from mdbrag import Bridge

# Connect to MariaDB
bridge = Bridge("mariadb+pymysql://user:pass@localhost:3306/mydb")

# Vectorize your data (bring your own vectors)
vectors = [[0.1, 0.2, ...], [0.3, 0.4, ...]]  # list[list[float]]
bridge.vectorize(
    source_table="clientes",
    fields=["notas", "descripcion"],
    vectors=vectors
)

# Search using pre-computed query vector
results = bridge.search(
    query_vector=[0.1, 0.2, ...],
    table_name="clientes_vectors",
    top_k=5
)
```

## How it works

mdb-rag uses the bridge pattern: you generate embeddings using your preferred model (OpenAI, sentence-transformers, etc.) and pass them to mdb-rag. The library handles storage and HNSW indexing directly in MariaDB, enabling semantic search without any external services or data migration.

## Contributing

```bash
git clone https://github.com/gaboexe0/mdb-rag
cd mdb-rag
pip install -e ".[dev]"
pytest
```

Requires MariaDB 11.8+ for integration testing.

Clone the repo, open issues, PRs welcome.

## License

MIT