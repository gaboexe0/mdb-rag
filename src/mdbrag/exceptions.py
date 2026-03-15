"""Custom exceptions for mdb-rag."""


class MdbRagError(Exception):
    """Base exception for mdb-rag library."""

    pass


class ConnectionError(MdbRagError):
    """Raised when connection to MariaDB fails."""

    pass


class VersionError(MdbRagError):
    """Raised when MariaDB version is not supported."""

    pass


class UnsupportedModelError(MdbRagError):
    """Raised when embedding model is not supported."""

    pass


class TableNotFoundError(MdbRagError):
    """Raised when source table does not exist."""

    pass


class ColumnNotFoundError(MdbRagError):
    """Raised when specified column does not exist in table."""

    pass


class NoVectorTableError(MdbRagError):
    """Raised when no vectorized table exists for search."""

    pass


class VectorizationError(MdbRagError):
    """Raised when vectorization operation fails."""

    pass
