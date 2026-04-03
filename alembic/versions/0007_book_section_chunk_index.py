"""add book/section to documents and chunk_index to chunks

Revision ID: 0007_book_section_chunk_index
Revises: 0006_chat_message_chunk_ids
Create Date: 2026-04-03 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision = "0007_book_section_chunk_index"
down_revision = "0006_chat_message_chunk_ids"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("documents", sa.Column("book",    sa.String(), nullable=True))
    op.add_column("documents", sa.Column("section", sa.String(), nullable=True))

    op.add_column("chunks", sa.Column("chunk_index", sa.Integer(), nullable=True))

    # index for fast ordered neighbor lookups during context expansion
    op.create_index(
        "chunks_document_id_chunk_index_idx",
        "chunks",
        ["document_id", "chunk_index"],
    )


def downgrade():
    op.drop_index("chunks_document_id_chunk_index_idx", table_name="chunks")
    op.drop_column("chunks", "chunk_index")
    op.drop_column("documents", "section")
    op.drop_column("documents", "book")
