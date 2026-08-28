from alembic import op
import sqlalchemy as sa


revision = "xxxxxxxx"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "document_chunks",
        sa.Column(
            "chunk_index",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.execute("""
        WITH numbered AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY document_id
                    ORDER BY id
                ) - 1 AS new_chunk_index
            FROM document_chunks
        )
        UPDATE document_chunks dc
        SET chunk_index = numbered.new_chunk_index
        FROM numbered
        WHERE dc.id = numbered.id
    """)

    op.alter_column(
        "document_chunks",
        "chunk_index",
        nullable=False,
    )


def downgrade():
    op.drop_column(
        "document_chunks",
        "chunk_index",
    )