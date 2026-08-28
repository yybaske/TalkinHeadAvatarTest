"""add pg trgm search

Revision ID: 82ea1dccb7fb
Revises: xxxxxxxx
Create Date: 2026-08-28 12:34:51.601884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82ea1dccb7fb'
down_revision: Union[str, Sequence[str], None] = 'xxxxxxxx'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS pg_trgm
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_document_chunks_content_trgm
        ON document_chunks
        USING gin (content gin_trgm_ops)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS
            idx_document_chunks_content_trgm
        """
    )

    op.execute(
        """
        DROP EXTENSION IF EXISTS pg_trgm
        """
    )