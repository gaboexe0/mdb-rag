"""Pydantic models for mdb-rag configuration and data structures."""

from pydantic import BaseModel, Field


class VectorizeConfig(BaseModel):
    """Configuration for vectorization operation."""

    source_table: str = Field(..., description="Name of the table to vectorize")
    fields: list[str] = Field(..., min_length=1, description="Text columns to vectorize")
    vectors: list[list[float]] = Field(..., description="Pre-computed embedding vectors")


class SearchConfig(BaseModel):
    """Configuration for search operation."""

    query_vector: list[float] = Field(..., description="Pre-computed query vector")
    table_name: str = Field(..., description="Vector table to search")
    top_k: int = Field(default=5, ge=1, le=100, description="Number of results to return")


class SearchResult(BaseModel):
    """Single search result from semantic search."""

    original_id: int = Field(..., description="ID from original table")
    combined_text: str = Field(..., description="Combined text from original fields")
    similarity: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    rank: int = Field(..., ge=1, description="Result rank (1-based)")


class VectorizeResult(BaseModel):
    """Result from vectorization operation."""

    table_name: str = Field(..., description="Name of created vector table")
    row_count: int = Field(..., ge=0, description="Number of rows vectorized")
    vector_dim: int = Field(..., description="Dimension of embedding vectors")
