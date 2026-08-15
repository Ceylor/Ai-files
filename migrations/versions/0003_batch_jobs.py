"""add batch_jobs table and videos.batch_job_id

Revision ID: 0003_batch_jobs
Revises: 0002_frame_embeddings
Create Date: 2025-01-03 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_batch_jobs"
down_revision: Union[str, None] = "0002_frame_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет таблицу batch_jobs и поле videos.batch_job_id."""
    # Новая таблица пакетных задач.
    op.create_table(
        "batch_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("folder_path", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("total_videos", sa.Integer(), server_default="0", nullable=False),
        sa.Column("processed_videos", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Поле batch_job_id в videos (FK на batch_jobs.id).
    # render_as_batch задаётся в env.py (для поддержки SQLite ALTER TABLE).
    with op.batch_alter_table("videos") as batch_op:
        batch_op.add_column(sa.Column("batch_job_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_videos_batch_job_id",
            "batch_jobs",
            ["batch_job_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Удаляет поле videos.batch_job_id и таблицу batch_jobs."""
    with op.batch_alter_table("videos") as batch_op:
        batch_op.drop_constraint("fk_videos_batch_job_id", type_="foreignkey")
        batch_op.drop_column("batch_job_id")

    op.drop_table("batch_jobs")