"""Add email_mailbox and email_message tables

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-18 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6g7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    # Create email_mailbox table
    op.create_table(
        "email_mailbox",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("mailbox_address", sa.Text(), nullable=False),
        sa.Column("mailbox_type", sa.Text(), nullable=False, server_default="personal"),
        sa.Column("channel_id", sa.Text(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=True),
        sa.Column("webhook_token", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("access_control", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("last_email_at", sa.BigInteger(), nullable=True),
        sa.Column("email_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    
    # Create indexes for email_mailbox
    op.create_index("email_mailbox_user_id_idx", "email_mailbox", ["user_id"])
    op.create_index("email_mailbox_channel_id_idx", "email_mailbox", ["channel_id"])
    op.create_index("email_mailbox_webhook_token_idx", "email_mailbox", ["webhook_token"])
    
    # Create email_message table
    op.create_table(
        "email_message",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("mailbox_id", sa.Text(), nullable=False),
        sa.Column("channel_id", sa.Text(), nullable=False),
        sa.Column("message_id", sa.Text(), nullable=True),
        sa.Column("email_id", sa.Text(), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("sender", sa.Text(), nullable=True),
        sa.Column("sender_name", sa.Text(), nullable=True),
        sa.Column("recipients", sa.JSON(), nullable=True),
        sa.Column("cc", sa.JSON(), nullable=True),
        sa.Column("body_preview", sa.Text(), nullable=True),
        sa.Column("has_attachments", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("attachments", sa.JSON(), nullable=True),
        sa.Column("received_at", sa.BigInteger(), nullable=True),
        sa.Column("importance", sa.Text(), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("agent_response", sa.Text(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    
    # Create indexes for email_message
    op.create_index("email_message_mailbox_id_idx", "email_message", ["mailbox_id"])
    op.create_index("email_message_channel_id_idx", "email_message", ["channel_id"])
    op.create_index("email_message_message_id_idx", "email_message", ["message_id"])


def downgrade():
    # Drop email_message indexes and table
    op.drop_index("email_message_message_id_idx", table_name="email_message")
    op.drop_index("email_message_channel_id_idx", table_name="email_message")
    op.drop_index("email_message_mailbox_id_idx", table_name="email_message")
    op.drop_table("email_message")
    
    # Drop email_mailbox indexes and table
    op.drop_index("email_mailbox_webhook_token_idx", table_name="email_mailbox")
    op.drop_index("email_mailbox_channel_id_idx", table_name="email_mailbox")
    op.drop_index("email_mailbox_user_id_idx", table_name="email_mailbox")
    op.drop_table("email_mailbox")

