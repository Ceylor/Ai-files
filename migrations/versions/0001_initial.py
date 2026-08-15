"""initial schema: categories, videos, learning_patterns, processing_history, user_feedback

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создание всех таблиц БД."""
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("resolution", sa.String(length=32), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("upload_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("extra_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_path"),
    )

    op.create_table(
        "learning_patterns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("vector", sa.JSON(), nullable=True),
        sa.Column("structure", sa.JSON(), nullable=True),
        sa.Column("tempo", sa.Float(), nullable=True),
        sa.Column("transitions", sa.JSON(), nullable=True),
        sa.Column("color_profile", sa.JSON(), nullable=True),
        sa.Column("music_profile", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "processing_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("input_video_ids", sa.JSON(), nullable=True),
        sa.Column("output_video_path", sa.String(length=1024), nullable=True),
        sa.Column("used_pattern_ids", sa.JSON(), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id"),
    )


def downgrade() -> None:
    """Удаление всех таблиц в обратном порядке."""
    op.drop_table("user_feedback")
    op.drop_table("processing_history")
    op.drop_table("learning_patterns")
    op.drop_table("videos")
    op.drop_table("categories")