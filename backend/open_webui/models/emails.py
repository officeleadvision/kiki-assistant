import json
import time
import uuid
from typing import Optional, List

from open_webui.internal.db import Base, get_db
from open_webui.models.groups import Groups

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON
from sqlalchemy import or_, func, select, and_

####################
# EmailMailbox DB Schema
####################


class EmailMailbox(Base):
    __tablename__ = "email_mailbox"

    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text, nullable=False)  # Owner of this mailbox config
    
    name = Column(Text, nullable=False)  # Display name for the mailbox
    description = Column(Text, nullable=True)
    
    mailbox_address = Column(Text, nullable=False)  # Email address to watch
    mailbox_type = Column(Text, nullable=False, default="personal")  # "personal" or "shared"
    
    channel_id = Column(Text, nullable=False)  # Associated channel for this mailbox
    
    # Model to use for processing emails
    model_id = Column(Text, nullable=True)
    
    # Webhook token for Power Automate
    webhook_token = Column(Text, nullable=False)
    
    # Configuration for email processing
    data = Column(JSON, nullable=True)  # Additional config (filters, auto-reply settings, etc.)
    meta = Column(JSON, nullable=True)
    access_control = Column(JSON, nullable=True)
    
    is_active = Column(Boolean, nullable=False, default=True)
    
    last_email_at = Column(BigInteger, nullable=True)  # Last email received timestamp
    email_count = Column(BigInteger, nullable=False, default=0)  # Total emails received
    
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class EmailMailboxModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    
    name: str
    description: Optional[str] = None
    
    mailbox_address: str
    mailbox_type: str = "personal"
    
    channel_id: str
    
    model_id: Optional[str] = None
    
    webhook_token: str
    
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None
    
    is_active: bool = True
    
    last_email_at: Optional[int] = None
    email_count: int = 0
    
    created_at: int
    updated_at: int


####################
# EmailMessage DB Schema - stores email metadata for reference
####################


class EmailMessage(Base):
    __tablename__ = "email_message"

    id = Column(Text, primary_key=True, unique=True)
    mailbox_id = Column(Text, nullable=False)
    channel_id = Column(Text, nullable=False)
    message_id = Column(Text, nullable=True)  # ID of the channel message created
    
    # Email metadata
    email_id = Column(Text, nullable=True)  # Original email ID from Exchange
    subject = Column(Text, nullable=True)
    sender = Column(Text, nullable=True)  # Sender email address
    sender_name = Column(Text, nullable=True)
    recipients = Column(JSON, nullable=True)  # List of recipients
    cc = Column(JSON, nullable=True)
    
    body_preview = Column(Text, nullable=True)  # First 500 chars of body
    has_attachments = Column(Boolean, nullable=False, default=False)
    attachments = Column(JSON, nullable=True)  # Attachment metadata
    
    received_at = Column(BigInteger, nullable=True)  # When email was received in Exchange
    importance = Column(Text, nullable=True)  # low, normal, high
    
    # Processing status
    processed = Column(Boolean, nullable=False, default=False)
    agent_response = Column(Text, nullable=True)  # Summary of agent's response
    
    data = Column(JSON, nullable=True)  # Full email data from Power Automate
    meta = Column(JSON, nullable=True)
    
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class EmailMessageModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mailbox_id: str
    channel_id: str
    message_id: Optional[str] = None
    
    email_id: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    sender_name: Optional[str] = None
    recipients: Optional[list] = None
    cc: Optional[list] = None
    
    body_preview: Optional[str] = None
    has_attachments: bool = False
    attachments: Optional[list] = None
    
    received_at: Optional[int] = None
    importance: Optional[str] = None
    
    processed: bool = False
    agent_response: Optional[str] = None
    
    data: Optional[dict] = None
    meta: Optional[dict] = None
    
    created_at: int
    updated_at: int


####################
# Forms
####################


class EmailMailboxForm(BaseModel):
    name: str
    description: Optional[str] = None
    mailbox_address: str
    mailbox_type: str = "personal"  # "personal" or "shared"
    channel_id: str
    model_id: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None


class EmailMailboxUpdateForm(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model_id: Optional[str] = None
    is_active: Optional[bool] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None


class IncomingEmailForm(BaseModel):
    """Form for receiving emails from Power Automate webhook"""
    email_id: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    sender_name: Optional[str] = None
    recipients: Optional[list] = None
    cc: Optional[list] = None
    body: Optional[str] = None
    body_preview: Optional[str] = None
    html_body: Optional[str] = None
    has_attachments: bool = False
    attachments: Optional[list] = None
    received_at: Optional[str] = None  # ISO format date string
    importance: Optional[str] = "normal"
    conversation_id: Optional[str] = None
    internet_message_id: Optional[str] = None


class EmailMailboxResponse(EmailMailboxModel):
    """Response with additional computed fields"""
    channel_name: Optional[str] = None


####################
# Table Operations
####################


class EmailMailboxTable:
    
    def insert_new_mailbox(
        self, form_data: EmailMailboxForm, user_id: str
    ) -> Optional[EmailMailboxModel]:
        with get_db() as db:
            mailbox = EmailMailboxModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "webhook_token": str(uuid.uuid4()),
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )
            new_mailbox = EmailMailbox(**mailbox.model_dump())
            db.add(new_mailbox)
            db.commit()
            db.refresh(new_mailbox)
            return EmailMailboxModel.model_validate(new_mailbox)

    def get_mailboxes(self) -> List[EmailMailboxModel]:
        with get_db() as db:
            mailboxes = db.query(EmailMailbox).all()
            return [EmailMailboxModel.model_validate(m) for m in mailboxes]

    def get_mailboxes_by_user_id(self, user_id: str) -> List[EmailMailboxModel]:
        with get_db() as db:
            user_group_ids = [
                group.id for group in Groups.get_groups_by_member_id(user_id)
            ]
            
            # Get mailboxes owned by user
            query = db.query(EmailMailbox).filter(
                or_(
                    EmailMailbox.user_id == user_id,
                    EmailMailbox.access_control.is_(None),
                )
            )
            
            mailboxes = query.all()
            return [EmailMailboxModel.model_validate(m) for m in mailboxes]

    def get_mailbox_by_id(self, id: str) -> Optional[EmailMailboxModel]:
        with get_db() as db:
            mailbox = db.query(EmailMailbox).filter(EmailMailbox.id == id).first()
            return EmailMailboxModel.model_validate(mailbox) if mailbox else None

    def get_mailbox_by_webhook_token(self, token: str) -> Optional[EmailMailboxModel]:
        with get_db() as db:
            mailbox = db.query(EmailMailbox).filter(
                EmailMailbox.webhook_token == token,
                EmailMailbox.is_active == True
            ).first()
            return EmailMailboxModel.model_validate(mailbox) if mailbox else None

    def get_mailbox_by_channel_id(self, channel_id: str) -> Optional[EmailMailboxModel]:
        with get_db() as db:
            mailbox = db.query(EmailMailbox).filter(
                EmailMailbox.channel_id == channel_id
            ).first()
            return EmailMailboxModel.model_validate(mailbox) if mailbox else None

    def update_mailbox_by_id(
        self, id: str, form_data: EmailMailboxUpdateForm
    ) -> Optional[EmailMailboxModel]:
        with get_db() as db:
            mailbox = db.query(EmailMailbox).filter(EmailMailbox.id == id).first()
            if not mailbox:
                return None
            
            update_data = form_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if value is not None:
                    setattr(mailbox, key, value)
            
            mailbox.updated_at = int(time.time_ns())
            db.commit()
            db.refresh(mailbox)
            return EmailMailboxModel.model_validate(mailbox)

    def regenerate_webhook_token(self, id: str) -> Optional[str]:
        with get_db() as db:
            mailbox = db.query(EmailMailbox).filter(EmailMailbox.id == id).first()
            if not mailbox:
                return None
            
            new_token = str(uuid.uuid4())
            mailbox.webhook_token = new_token
            mailbox.updated_at = int(time.time_ns())
            db.commit()
            return new_token

    def increment_email_count(self, id: str) -> bool:
        with get_db() as db:
            mailbox = db.query(EmailMailbox).filter(EmailMailbox.id == id).first()
            if not mailbox:
                return False
            
            mailbox.email_count = (mailbox.email_count or 0) + 1
            mailbox.last_email_at = int(time.time_ns())
            mailbox.updated_at = int(time.time_ns())
            db.commit()
            return True

    def delete_mailbox_by_id(self, id: str) -> bool:
        with get_db() as db:
            result = db.query(EmailMailbox).filter(EmailMailbox.id == id).delete()
            db.commit()
            return result > 0


class EmailMessageTable:
    
    def insert_new_email(
        self, mailbox_id: str, channel_id: str, form_data: IncomingEmailForm, message_id: Optional[str] = None
    ) -> Optional[EmailMessageModel]:
        with get_db() as db:
            # Parse received_at from ISO format if provided
            received_at = None
            if form_data.received_at:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(form_data.received_at.replace('Z', '+00:00'))
                    received_at = int(dt.timestamp() * 1e9)  # Convert to nanoseconds
                except:
                    received_at = int(time.time_ns())
            
            email = EmailMessageModel(
                **{
                    "id": str(uuid.uuid4()),
                    "mailbox_id": mailbox_id,
                    "channel_id": channel_id,
                    "message_id": message_id,
                    "email_id": form_data.email_id,
                    "subject": form_data.subject,
                    "sender": form_data.sender,
                    "sender_name": form_data.sender_name,
                    "recipients": form_data.recipients,
                    "cc": form_data.cc,
                    "body_preview": (form_data.body_preview or form_data.body or "")[:500],
                    "has_attachments": form_data.has_attachments,
                    "attachments": form_data.attachments,
                    "received_at": received_at,
                    "importance": form_data.importance,
                    "data": form_data.model_dump(),
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )
            new_email = EmailMessage(**email.model_dump())
            db.add(new_email)
            db.commit()
            db.refresh(new_email)
            return EmailMessageModel.model_validate(new_email)

    def get_emails_by_mailbox_id(
        self, mailbox_id: str, skip: int = 0, limit: int = 50
    ) -> List[EmailMessageModel]:
        with get_db() as db:
            emails = (
                db.query(EmailMessage)
                .filter(EmailMessage.mailbox_id == mailbox_id)
                .order_by(EmailMessage.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [EmailMessageModel.model_validate(e) for e in emails]

    def get_emails_by_channel_id(
        self, channel_id: str, skip: int = 0, limit: int = 50
    ) -> List[EmailMessageModel]:
        with get_db() as db:
            emails = (
                db.query(EmailMessage)
                .filter(EmailMessage.channel_id == channel_id)
                .order_by(EmailMessage.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [EmailMessageModel.model_validate(e) for e in emails]

    def get_email_by_id(self, id: str) -> Optional[EmailMessageModel]:
        with get_db() as db:
            email = db.query(EmailMessage).filter(EmailMessage.id == id).first()
            return EmailMessageModel.model_validate(email) if email else None

    def update_email_message_id(self, id: str, message_id: str) -> bool:
        with get_db() as db:
            email = db.query(EmailMessage).filter(EmailMessage.id == id).first()
            if not email:
                return False
            email.message_id = message_id
            email.updated_at = int(time.time_ns())
            db.commit()
            return True

    def update_email_processed(
        self, id: str, processed: bool, agent_response: Optional[str] = None
    ) -> bool:
        with get_db() as db:
            email = db.query(EmailMessage).filter(EmailMessage.id == id).first()
            if not email:
                return False
            email.processed = processed
            if agent_response:
                email.agent_response = agent_response
            email.updated_at = int(time.time_ns())
            db.commit()
            return True

    def delete_email_by_id(self, id: str) -> bool:
        with get_db() as db:
            result = db.query(EmailMessage).filter(EmailMessage.id == id).delete()
            db.commit()
            return result > 0

    def delete_emails_by_mailbox_id(self, mailbox_id: str) -> int:
        with get_db() as db:
            result = db.query(EmailMessage).filter(
                EmailMessage.mailbox_id == mailbox_id
            ).delete()
            db.commit()
            return result


EmailMailboxes = EmailMailboxTable()
EmailMessages = EmailMessageTable()

