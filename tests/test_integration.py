"""Integration tests for bridge.py with real MariaDB."""

import time

import pytest
import pymysql
from sqlalchemy import text

from mdbrag.bridge import Bridge


def wait_for_db(retries=15, delay=3):
    """Wait for MariaDB to be ready."""
    for _ in range(retries):
        try:
            pymysql.connect(
                host="localhost", port=3307, user="testuser", password="testpass", database="testdb"
            )
            return
        except Exception:
            time.sleep(delay)
    raise RuntimeError("MariaDB not ready after retries")


@pytest.fixture
def bridge():
    """Create Bridge connected to test database."""
    wait_for_db()
    return Bridge("mariadb+pymysql://testuser:testpass@localhost:3307/testdb")


@pytest.fixture
def setup_test_table(bridge):
    """Create test table and insert sample data."""
    with bridge._engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_clientes"))
        conn.execute(text("DROP TABLE IF EXISTS test_clientes_vectors"))
        conn.execute(
            text("CREATE TABLE test_clientes (id INT AUTO_INCREMENT PRIMARY KEY, notas TEXT)")
        )
        conn.execute(
            text(
                "INSERT INTO test_clientes (notas) VALUES "
                "('cliente con problema de facturacion'), "
                "('cliente satisfecho con el servicio'), "
                "('cliente quejoso por delay en entrega')"
            )
        )
        conn.commit()
    yield
    with bridge._engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_clientes"))
        conn.execute(text("DROP TABLE IF EXISTS test_clientes_vectors"))
        conn.commit()


@pytest.mark.integration
def test_validate_version(bridge):
    """Test that Bridge connects to MariaDB 11.8+."""
    with bridge._engine.connect() as conn:
        result = conn.execute(text("SELECT VERSION()"))
        version = result.fetchone()[0]
        assert "11.8" in version


@pytest.mark.integration
def test_vectorize_creates_table(bridge, setup_test_table):
    """Test that vectorize creates the vector table."""
    vectors = [
        [0.1, 0.2, 0.3, 0.4],
        [0.5, 0.6, 0.7, 0.8],
        [0.9, 1.0, 1.1, 1.2],
    ]
    result = bridge.vectorize(
        source_table="test_clientes",
        fields=["notas"],
        vectors=vectors,
    )

    assert result["table_name"] == "test_clientes_vectors"
    assert result["row_count"] == 3
    assert result["vector_dim"] == 4

    with bridge._engine.connect() as conn:
        check = conn.execute(text("SHOW TABLES LIKE 'test_clientes_vectors'"))
        assert check.fetchone() is not None


@pytest.mark.integration
def test_search_returns_results(bridge, setup_test_table):
    """Test that search returns top_k results."""
    vectors = [
        [0.1, 0.2, 0.3, 0.4],
        [0.5, 0.6, 0.7, 0.8],
        [0.9, 1.0, 1.1, 1.2],
    ]
    bridge.vectorize(
        source_table="test_clientes",
        fields=["notas"],
        vectors=vectors,
    )

    query_vector = [0.1, 0.2, 0.3, 0.4]
    results = bridge.search(
        query_vector=query_vector,
        table_name="test_clientes_vectors",
        top_k=3,
    )

    assert isinstance(results, list)
    assert len(results) == 3
    assert all("similarity" in r for r in results)
    assert all("rank" in r for r in results)
    assert results[0]["rank"] == 1
    assert results[0]["similarity"] >= 0
