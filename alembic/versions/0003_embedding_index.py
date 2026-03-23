"""add hnsw index for chunk embeddings

Revision ID: 0003_chunk_embedding_hnsw
Revises: 0002_create_tables
Create Date: 2026-03-22 22:33:45.123456
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_chunk_embedding_hnsw"
down_revision: Union[str, Sequence[str], None] = "0002_create_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_cosine_idx
        ON chunks
        USING hnsw (embedding vector_cosine_ops)
        """
    )

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS chunks_embedding_hnsw_cosine_idx")