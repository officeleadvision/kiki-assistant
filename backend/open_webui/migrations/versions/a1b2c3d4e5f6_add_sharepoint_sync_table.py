"""Add sharepoint_sync table

Revision ID: a1b2c3d4e5f6
Revises: 018012973d35
Create Date: 2025-01-17 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "018012973d35"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sharepoint_sync",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("knowledge_id", sa.Text(), nullable=False),
        sa.Column("drive_id", sa.Text(), nullable=False),
        sa.Column("item_id", sa.Text(), nullable=False),
        sa.Column("folder_path", sa.Text(), nullable=True),
        sa.Column("sharepoint_endpoint", sa.Text(), nullable=False),
        sa.Column("last_sync_at", sa.BigInteger(), nullable=True),
        sa.Column("file_count", sa.BigInteger(), default=0),
        sa.Column("sync_status", sa.Text(), default="idle"),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )

    # Create indexes for common queries
    op.create_index("sp_sync_user_id_idx", "sharepoint_sync", ["user_id"])
    op.create_index("sp_sync_knowledge_id_idx", "sharepoint_sync", ["knowledge_id"])


def downgrade():
    op.drop_index("sp_sync_knowledge_id_idx", table_name="sharepoint_sync")
    op.drop_index("sp_sync_user_id_idx", table_name="sharepoint_sync")
    op.drop_table("sharepoint_sync")

