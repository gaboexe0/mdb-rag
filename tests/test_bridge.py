"""Tests for bridge.py using mocked SQLAlchemy engine."""

from unittest.mock import MagicMock, patch

import pytest

from mdbrag.bridge import Bridge
from mdbrag.exceptions import NoVectorTableError, VectorizationError, VersionError


@pytest.fixture
def bridge_with_mock_engine():
    """Create a Bridge instance with a mocked engine at version 11.8."""
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = ["11.8.0-MariaDB"]
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    with patch("mdbrag.bridge.create_engine", return_value=mock_engine):
        bridge = Bridge("mariadb+pymysql://user:pass@localhost:3306/mydb")
        bridge._mock_conn = mock_conn
        return bridge


class TestBridgeInit:
    def test_raises_value_error_if_not_mariadb_uri(self):
        with pytest.raises(ValueError, match="must be a MariaDB URI"):
            Bridge("mysql://user:pass@localhost:3306/mydb")

    def test_raises_value_error_for_invalid_uri(self):
        with pytest.raises(ValueError, match="must be a MariaDB URI"):
            Bridge("invalid://something")

    @patch("mdbrag.bridge.create_engine")
    def test_creates_engine_with_valid_uri(self, mock_create_engine):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ["11.8.0-MariaDB"]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        bridge = Bridge("mariadb+pymysql://user:pass@localhost:3306/mydb")

        mock_create_engine.assert_called_once_with(
            "mariadb+pymysql://user:pass@localhost:3306/mydb"
        )
        assert bridge._engine == mock_engine


class TestValidateVersion:
    @patch("mdbrag.bridge.create_engine")
    def test_raises_version_error_if_below_11_8(self, mock_create_engine):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ["10.11.0-MariaDB"]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(VersionError, match="11.8"):
            Bridge("mariadb+pymysql://user:pass@localhost:3306/mydb")

    @patch("mdbrag.bridge.create_engine")
    def test_raises_version_error_for_11_7(self, mock_create_engine):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ["11.7.0-MariaDB"]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(VersionError, match="11.8"):
            Bridge("mariadb+pymysql://user:pass@localhost:3306/mydb")

    @patch("mdbrag.bridge.create_engine")
    def test_accepts_version_11_8(self, mock_create_engine):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ["11.8.0-MariaDB"]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        bridge = Bridge("mariadb+pymysql://user:pass@localhost:3306/mydb")
        assert bridge is not None


class TestVectorize:
    def test_raises_vectorization_error_if_vectors_empty(self, bridge_with_mock_engine):
        bridge = bridge_with_mock_engine
        mock_conn = bridge._mock_conn

        mock_cols_result = MagicMock()
        mock_cols_result.fetchall.return_value = [("id",), ("name",)]

        mock_source = MagicMock()
        mock_source.fetchall.return_value = [MagicMock(_mapping={"id": 1, "name": "test"})]
        mock_source.keys.return_value = ["id", "name"]

        with patch.object(bridge._engine, "connect") as mock_connect:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_connect.return_value = mock_ctx

            mock_conn.execute.side_effect = [
                mock_cols_result,
                mock_source,
            ]

            with pytest.raises(VectorizationError, match="No vectors provided"):
                bridge.vectorize("test_table", ["name"], vectors=[])

    def test_raises_vectorization_error_if_vectors_count_mismatch(self, bridge_with_mock_engine):
        bridge = bridge_with_mock_engine
        mock_conn = bridge._mock_conn

        with patch.object(bridge._engine, "connect") as mock_connect:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_connect.return_value = mock_ctx

            mock_cols = MagicMock()
            mock_cols.fetchall.return_value = [("id",), ("name",)]
            mock_source = MagicMock()
            mock_source.fetchall.return_value = [
                MagicMock(_mapping={"id": 1, "name": "a"}),
                MagicMock(_mapping={"id": 2, "name": "b"}),
            ]
            mock_source.keys.return_value = ["id", "name"]
            mock_conn.execute.side_effect = [mock_cols, mock_source]

            vectors = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

            with pytest.raises(VectorizationError, match="does not match number of rows"):
                bridge.vectorize("test_table", ["name"], vectors=vectors)

    def test_vectorize_returns_correct_dict_structure(self, bridge_with_mock_engine):
        bridge = bridge_with_mock_engine
        mock_conn = bridge._mock_conn

        with patch.object(bridge._engine, "connect") as mock_connect:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_connect.return_value = mock_ctx

            mock_cols = MagicMock()
            mock_cols.fetchall.return_value = [("id",), ("name",)]
            mock_source = MagicMock()
            mock_source.fetchall.return_value = [
                MagicMock(_mapping={"id": 1, "name": "test1"}),
                MagicMock(_mapping={"id": 2, "name": "test2"}),
            ]
            mock_source.keys.return_value = ["id", "name"]
            mock_conn.execute.side_effect = [mock_cols, mock_source, None, None, None, None, None]

            vectors = [[0.1, 0.2], [0.3, 0.4]]
            result = bridge.vectorize("test_table", ["name"], vectors=vectors)

            assert "table_name" in result
            assert "row_count" in result
            assert "vector_dim" in result
            assert result["table_name"] == "test_table_vectors"
            assert result["row_count"] == 2
            assert result["vector_dim"] == 2


class TestSearch:
    def test_search_raises_no_vector_table_error(self, bridge_with_mock_engine):
        bridge = bridge_with_mock_engine
        mock_conn = bridge._mock_conn

        with patch.object(bridge._engine, "connect") as mock_connect:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_connect.return_value = mock_ctx

            mock_check = MagicMock()
            mock_check.fetchone.return_value = None
            mock_conn.execute.return_value = mock_check

            with pytest.raises(NoVectorTableError, match="does not exist"):
                bridge.search(query_vector=[0.1, 0.2], table_name="nonexistent_vectors")

    def test_search_returns_correct_list_structure(self, bridge_with_mock_engine):
        bridge = bridge_with_mock_engine
        mock_conn = bridge._mock_conn

        with patch.object(bridge._engine, "connect") as mock_connect:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_connect.return_value = mock_ctx

            mock_check = MagicMock()
            mock_check.fetchone.return_value = ["exists"]
            mock_search = MagicMock()
            mock_search.fetchall.return_value = [
                (1, "text1", 0.1),
                (2, "text2", 0.2),
            ]
            mock_conn.execute.side_effect = [mock_check, mock_search]

            result = bridge.search(query_vector=[0.1, 0.2], table_name="test_vectors", top_k=5)

            assert isinstance(result, list)
            assert len(result) == 2
            assert "original_id" in result[0]
            assert "combined_text" in result[0]
            assert "similarity" in result[0]
            assert "rank" in result[0]
            assert result[0]["rank"] == 1
            assert result[1]["rank"] == 2
