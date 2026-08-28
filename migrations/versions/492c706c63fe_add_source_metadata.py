"""add source metadata

Revision ID: 492c706c63fe
Revises: 82ea1dccb7fb
Create Date: 2026-08-28 12:49:22.242291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '492c706c63fe'
down_revision: Union[str, Sequence[str], None] = '82ea1dccb7fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column(
            "page_number",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "document_chunks",
        sa.Column(
            "section_title",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "document_chunks",
        "section_title",
    )

    op.drop_column(
        "document_chunks",
        "page_number",
    )