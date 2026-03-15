# What is mdb-rag?

mdb-rag is a Python library that bridges legacy MySQL/MariaDB data into RAG 
pipelines without migration.

## The problem

70-80% of legacy data in LATAM lives in MySQL/MariaDB. Most of it predates 
the AI era and has no path to semantic search without expensive ETL to 
PostgreSQL or external vector databases like Pinecone or Weaviate.

The typical options are:

- Migrate to PostgreSQL and use pgvector
- Set up a separate vector database and sync your data
- Pay for managed vector search on top of your existing stack

All three options require touching infrastructure that works, spending 
engineering time you don't have, and paying for services you didn't budget for.

## The solution

MariaDB 11.8 introduced native VECTOR type and HNSW indexes. mdb-rag uses 
this to turn your existing MariaDB instance into a vector database.

Your data stays where it is. You add one dependency and you're inside a 
RAG pipeline.

## What about MySQL?

MySQL community edition does not support native VECTOR type or HNSW indexes.
Oracle's vector search is exclusive to MySQL HeatWave, a proprietary cloud
product that requires vendor lock-in and a budget most teams don't have.

MySQL community development has stalled since Oracle's acquisition. Security
patches still ship, but meaningful innovation stopped years ago. MariaDB is
where the MySQL community actually lives now.

The good news: MariaDB 11.8 is a drop-in replacement for MySQL. Same protocol,
same SQL dialect, same drivers. Migrating is a server swap, not a rewrite.

**Migration effort from MySQL to MariaDB 11.8:**

| What changes | What stays the same |
|---|---|
| Database server binary | All your SQL queries |
| my.cnf → mariadb.cnf | Your application code |
| | Your ORM and drivers |
| | Your data, untouched |

Switching to MariaDB costs an afternoon. Staying on MySQL costs you access
to every AI feature the ecosystem is building right now.

## What mdb-rag is not

- It does not generate embeddings. You bring your own vectors.
- It does not replace Redis or a dedicated vector DB for latency-critical 
workloads.
- It does not support MySQL community edition. MariaDB 11.8+ only.