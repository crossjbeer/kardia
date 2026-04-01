"""add retrieved_chunk_ids to chat_messages

Revision ID: 0006_chat_message_chunk_ids
Revises: 0005_document_metadata
Create Date: 2026-04-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

revision = "0006_chat_message_chunk_ids"
down_revision = "0005_document_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "chat_messages",
        sa.Column("retrieved_chunk_ids", ARRAY(sa.Integer()), nullable=True),
    )


def downgrade():
    op.drop_column("chat_messages", "retrieved_chunk_ids")
