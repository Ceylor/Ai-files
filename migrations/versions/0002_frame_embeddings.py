"""add frame_embeddings + analysis fields to videos

Revision ID: 0002_frame_embeddings
Revises: 0001_initial
Create Date: 2025-01-02 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_frame_embeddings"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет таблицу frame_embeddings и поля анализа в videos."""
    # Новые поля анализа в videos.
    op.add_column("videos", sa.Column("analysis_results", sa.JSON(), nullable=True))
    op.add_column("videos", sa.Column("golden_moments", sa.JSON(), nullable=True))

    # Новая таблица frame_embeddings.
    op.create_table(
        "frame_embeddings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.Float(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Удаляет таблицу frame_embeddings и поля анализа из videos."""
    op.drop_table("frame_embeddings")
    op.drop_column("videos", "golden_moments")
    op.drop_column("videos", "analysis_results")