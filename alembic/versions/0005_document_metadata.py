"""add metadata columns to documents

Revision ID: 0005_document_metadata
Revises: 0004_chunk_fts
Create Date: 2026-03-25 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision = "0005_document_metadata"
down_revision = "0004_chunk_fts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("documents", sa.Column("corpus",      sa.String(), nullable=True))
    op.add_column("documents", sa.Column("campaign",    sa.String(), nullable=True))
    op.add_column("documents", sa.Column("tags",        sa.String(), nullable=True))
    op.add_column("documents", sa.Column("game_system", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("author",      sa.String(), nullable=True))


def downgrade():
    op.drop_column("documents", "author")
    op.drop_column("documents", "game_system")
    op.drop_column("documents", "tags")
    op.drop_column("documents", "campaign")
    op.drop_column("documents", "corpus")
