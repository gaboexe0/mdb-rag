"""mdb-rag: Bridge legacy MySQL/MariaDB data into RAG pipelines."""

from mdbrag.bridge import Bridge
from mdbrag.exceptions import (
    MdbRagError,
    ConnectionError,
    VersionError,
    UnsupportedModelError,
    TableNotFoundError,
    ColumnNotFoundError,
    NoVectorTableError,
    VectorizationError,
)
from mdbrag.models import SearchConfig, SearchResult, VectorizeConfig, VectorizeResult

__all__ = [
    "Bridge",
    "MdbRagError",
    "ConnectionError",
    "VersionError",
    "UnsupportedModelError",
    "TableNotFoundError",
    "ColumnNotFoundError",
    "NoVectorTableError",
    "VectorizationError",
    "SearchConfig",
    "SearchResult",
    "VectorizeConfig",
    "VectorizeResult",
]
__version__ = "0.1.0"
