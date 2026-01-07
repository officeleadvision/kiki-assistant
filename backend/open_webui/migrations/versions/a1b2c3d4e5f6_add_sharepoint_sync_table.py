"""Add sharepoint_sync table

Revision ID: a1b2c3d4e5f6
Revises: 018012973d35
Create Date: 2025-01-17 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "3e0e00844bb0"
branch_labels = None
depends_on = None


def _bind():
    return op.get_bind()


def _exists_index(bind, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in {index["name"] for index in inspector.get_indexes("sharepoint_sync")}


def _ensure_index(bind, name: str, columns: list[str]):
    if not _exists_index(bind, name):
        op.create_index(name, "sharepoint_sync", columns)


def upgrade():
    bind = _bind()
    has_table = bind.dialect.has_table(bind, "sharepoint_sync")

    if not has_table:
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

    # Create indexes for common queries if missing
    _ensure_index(bind, "sp_sync_user_id_idx", ["user_id"])
    _ensure_index(bind, "sp_sync_knowledge_id_idx", ["knowledge_id"])


def downgrade():
    bind = _bind()
    if not bind.dialect.has_table(bind, "sharepoint_sync"):
        return

    if _exists_index(bind, "sp_sync_knowledge_id_idx"):
        op.drop_index("sp_sync_knowledge_id_idx", table_name="sharepoint_sync")

    if _exists_index(bind, "sp_sync_user_id_idx"):
        op.drop_index("sp_sync_user_id_idx", table_name="sharepoint_sync")

    op.drop_table("sharepoint_sync")

