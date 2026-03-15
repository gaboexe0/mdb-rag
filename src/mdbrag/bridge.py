"""Bridge class for connecting to MariaDB and performing vector operations."""

from typing import Any

from sqlalchemy import create_engine, text

from mdbrag.exceptions import (
    ColumnNotFoundError,
    ConnectionError,
    NoVectorTableError,
    TableNotFoundError,
    VectorizationError,
    VersionError,
)


class Bridge:
    """Bridge class for connecting to MariaDB and performing vector operations.

    This class provides methods to store pre-computed vectors in MariaDB and perform
    semantic searches using HNSW vector indexes (MariaDB 11.8+).

    Example:
        >>> bridge = Bridge(connection_string="mariadb+pymysql://user:pass@localhost:3306/mydb")
        >>> bridge.vectorize(source_table="clientes", fields=["notas", "descripcion"], vectors=[[0.1, 0.2, ...], ...])
        >>> results = bridge.search(query_vector=[0.1, 0.2, ...], table_name="clientes_vectors", top_k=5)
    """

    def __init__(self, connection_string: str) -> None:
        """Initialize the Bridge with a MariaDB connection string.

        Args:
            connection_string: SQLAlchemy-compatible MariaDB connection string.
                Format: mariadb+pymysql://user:password@host:port/database

        Raises:
            ValueError: If connection_string is invalid or not a MariaDB URI.
            VersionError: If MariaDB version is below 11.8.
        """
        if not (
            connection_string.startswith("mariadb://")
            or connection_string.startswith("mariadb+pymysql://")
        ):
            raise ValueError("Connection string must be a MariaDB URI (mariadb+pymysql://...)")

        self._connection_string = connection_string
        self._engine = create_engine(connection_string)
        self._validate_version()

    def _validate_version(self) -> None:
        """Validate that MariaDB version is 11.8 or higher.

        Raises:
            VersionError: If MariaDB version is below 11.8.
        """
        with self._engine.connect() as conn:
            result = conn.execute(text("SELECT VERSION()"))
            version_row = result.fetchone()
            if not version_row:
                raise ConnectionError("Could not retrieve MariaDB version")

            version_str = version_row[0]

            if "-" in version_str:
                version_str = version_str.split("-")[0]

            parts = version_str.split(".")
            if len(parts) < 2:
                raise VersionError(f"Invalid MariaDB version format: {version_str}")

            major = int(parts[0])
            minor = int(parts[1])

            if major < 11 or (major == 11 and minor < 8):
                raise VersionError(
                    f"MariaDB version {major}.{minor} is not supported. "
                    "Version 11.8+ is required for HNSW vector indexes."
                )

    def _get_table_columns(self, table_name: str) -> list[str]:
        """Get list of column names for a table.

        Args:
            table_name: Name of the table.

        Returns:
            List of column names.

        Raises:
            TableNotFoundError: If table does not exist.
        """
        with self._engine.connect() as conn:
            result = conn.execute(text(f"SHOW COLUMNS FROM {table_name}"))
            columns = [row[0] for row in result.fetchall()]
            if not columns:
                raise TableNotFoundError(f"Table '{table_name}' does not exist")
            return columns

    def _validate_columns(self, table_name: str, fields: list[str]) -> None:
        """Validate that specified columns exist in the table.

        Args:
            table_name: Name of the table.
            fields: List of column names to validate.

        Raises:
            ColumnNotFoundError: If any column does not exist.
        """
        existing_columns = self._get_table_columns(table_name)
        missing_columns = [f for f in fields if f not in existing_columns]
        if missing_columns:
            raise ColumnNotFoundError(
                f"Columns not found in table '{table_name}': {missing_columns}"
            )

    def vectorize(
        self,
        source_table: str,
        fields: list[str],
        vectors: list[list[float]],
    ) -> dict[str, Any]:
        """Vectorize specified fields from a source table.

        Creates a new table with vector embeddings and sets up HNSW index
        for semantic search. The user provides pre-computed vectors.

        Args:
            source_table: Name of the existing table to vectorize.
            fields: List of text column names to include in vectorization.
            vectors: List of pre-computed embedding vectors (list of floats or numpy array).

        Returns:
            Dictionary containing vectorization results:
                - table_name: Name of the created vector table
                - row_count: Number of rows vectorized
                - vector_dim: Dimension of the embedding vectors

        Raises:
            TableNotFoundError: If source_table does not exist.
            ColumnNotFoundError: If any specified field does not exist.
            VectorizationError: If vectorization operation fails.
        """
        self._validate_columns(source_table, fields)

        with self._engine.connect() as conn:
            source_result = conn.execute(text(f"SELECT * FROM {source_table}"))
            rows = source_result.fetchall()
            column_names = list(source_result.keys())

            if not rows:
                return {
                    "table_name": f"{source_table}_vectors",
                    "row_count": 0,
                    "vector_dim": 1536,
                }

            texts_to_embed = []
            for row in rows:
                row_dict = dict(row._mapping)
                combined_text = " ".join(
                    str(row_dict[col]) for col in fields if col in column_names
                )
                texts_to_embed.append(combined_text)

            if not vectors:
                raise VectorizationError("No vectors provided")

            if len(vectors) != len(rows):
                raise VectorizationError(
                    f"Number of vectors ({len(vectors)}) does not match number of rows ({len(rows)})"
                )

            vector_dim = len(vectors[0])

            vector_table = f"{source_table}_vectors"

            conn.execute(text(f"DROP TABLE IF EXISTS {vector_table}"))

            create_table_sql = f"""
            CREATE TABLE {vector_table} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                original_id INT,
                combined_text TEXT,
                embedding VECTOR({vector_dim}) NOT NULL,
                VECTOR INDEX idx_vector (embedding)
            )
            """
            conn.execute(text(create_table_sql))

            for idx, (row, embedding) in enumerate(zip(rows, vectors)):
                original_id = row[0] if column_names else idx
                combined_text = texts_to_embed[idx]
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

                conn.execute(
                    text(f"""
                    INSERT INTO {vector_table} (original_id, combined_text, embedding)
                    VALUES (:original_id, :combined_text, Vec_FromText(:embedding))
                    """),
                    {
                        "original_id": original_id,
                        "combined_text": combined_text,
                        "embedding": embedding_str,
                    },
                )

            conn.commit()

            return {
                "table_name": vector_table,
                "row_count": len(rows),
                "vector_dim": vector_dim,
            }

    def search(
        self,
        query_vector: list[float],
        table_name: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Perform semantic search on vectorized data.

        Searches the specified vector table using a pre-computed query vector.
        Returns results ranked by semantic similarity.

        Args:
            query_vector: Pre-computed query vector for search.
            table_name: Name of the vector table to search.
            top_k: Number of top results to return. Defaults to 5.

        Returns:
            List of dictionaries containing search results:
                - original_id: ID from original table
                - combined_text: Combined text from original fields
                - similarity: Similarity score (0-1, higher is better)
                - rank: Position in results (1-based)

        Raises:
            NoVectorTableError: If vector table does not exist.
        """
        with self._engine.connect() as conn:
            check_result = conn.execute(text(f"SHOW TABLES LIKE '{table_name}'"))
            if not check_result.fetchone():
                raise NoVectorTableError(f"Vector table '{table_name}' does not exist")

        embedding_str = "[" + ",".join(str(x) for x in query_vector) + "]"

        with self._engine.connect() as conn:
            result = conn.execute(
                text(f"""
                SELECT original_id, combined_text,
                       VEC_DISTANCE_COSINE(embedding, Vec_FromText(:query_embedding)) as distance
                FROM {table_name}
                ORDER BY distance ASC
                LIMIT :top_k
                """),
                {"query_embedding": embedding_str, "top_k": top_k},
            )

            rows = result.fetchall()

            results = []
            for rank, row in enumerate(rows, start=1):
                results.append(
                    {
                        "original_id": row[0],
                        "combined_text": row[1],
                        "similarity": 1 - row[2],
                        "rank": rank,
                    }
                )

            return results
