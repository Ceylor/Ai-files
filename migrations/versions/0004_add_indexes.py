"""add performance indexes

Revision ID: 0004_add_indexes
Revises: 0003_batch_jobs
Create Date: 2025-01-04 00:00:00

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004_add_indexes"
down_revision: Union[str, None] = "0003_batch_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes on frequently queried columns."""
    op.create_index("ix_videos_status", "videos", ["status"])
    op.create_index("ix_videos_category_id", "videos", ["category_id"])
    op.create_index("ix_videos_batch_job_id", "videos", ["batch_job_id"])
    op.create_index("ix_videos_upload_date", "videos", ["upload_date"])
    op.create_index("ix_batch_jobs_status", "batch_jobs", ["status"])
    op.create_index("ix_batch_jobs_created_at", "batch_jobs", ["created_at"])
    op.create_index("ix_learning_patterns_category_id", "learning_patterns", ["category_id"])
    op.create_index("ix_frame_embeddings_video_id", "frame_embeddings", ["video_id"])


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index("ix_frame_embeddings_video_id", "frame_embeddings")
    op.drop_index("ix_learning_patterns_category_id", "learning_patterns")
    op.drop_index("ix_batch_jobs_created_at", "batch_jobs")
    op.drop_index("ix_batch_jobs_status", "batch_jobs")
    op.drop_index("ix_videos_upload_date", "videos")
    op.drop_index("ix_videos_batch_job_id", "videos")
    op.drop_index("ix_videos_category_id", "videos")
    op.drop_index("ix_videos_status", "videos")
