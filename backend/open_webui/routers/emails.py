import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel

from open_webui.socket.main import sio
from open_webui.models.users import (
    UserNameResponse,
    Users,
)
from open_webui.models.channels import (
    Channels,
    ChannelModel,
    CreateChannelForm,
)
from open_webui.models.messages import (
    Messages,
    MessageModel,
    MessageForm,
)
from open_webui.models.emails import (
    EmailMailboxes,
    EmailMailboxModel,
    EmailMailboxForm,
    EmailMailboxUpdateForm,
    EmailMailboxResponse,
    EmailMessages,
    EmailMessageModel,
    IncomingEmailForm,
)

from open_webui.constants import ERROR_MESSAGES

from open_webui.utils.models import get_all_models, get_filtered_models
from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Get Mailboxes
############################


@router.get("/", response_model=list[EmailMailboxResponse])
async def get_mailboxes(request: Request, user=Depends(get_verified_user)):
    """Get all email mailboxes accessible to the user"""
    if user.role == "admin":
        mailboxes = EmailMailboxes.get_mailboxes()
    else:
        mailboxes = EmailMailboxes.get_mailboxes_by_user_id(user.id)
    
    # Enrich with channel names
    result = []
    for mailbox in mailboxes:
        channel = Channels.get_channel_by_id(mailbox.channel_id)
        result.append(
            EmailMailboxResponse(
                **mailbox.model_dump(),
                channel_name=channel.name if channel else None,
            )
        )
    
    return result


############################
# Create Mailbox
############################


@router.post("/create", response_model=Optional[EmailMailboxModel])
async def create_mailbox(
    request: Request,
    form_data: EmailMailboxForm,
    user=Depends(get_verified_user),
):
    """Create a new email mailbox configuration"""
    if user.role != "admin" and not has_permission(
        user.id, "features.channels", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )
    
    # Verify the channel exists
    channel = Channels.get_channel_by_id(form_data.channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found",
        )
    
    # Check if mailbox already exists for this channel
    existing = EmailMailboxes.get_mailbox_by_channel_id(form_data.channel_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A mailbox already exists for this channel",
        )
    
    try:
        mailbox = EmailMailboxes.insert_new_mailbox(form_data, user.id)
        return mailbox
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


############################
# Get Mailbox By ID
############################


@router.get("/{id}", response_model=Optional[EmailMailboxResponse])
async def get_mailbox_by_id(id: str, user=Depends(get_verified_user)):
    """Get a specific mailbox by ID"""
    mailbox = EmailMailboxes.get_mailbox_by_id(id)
    if not mailbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    if (
        mailbox.user_id != user.id
        and user.role != "admin"
        and not has_access(user.id, "read", mailbox.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )
    
    channel = Channels.get_channel_by_id(mailbox.channel_id)
    return EmailMailboxResponse(
        **mailbox.model_dump(),
        channel_name=channel.name if channel else None,
    )


############################
# Update Mailbox
############################


@router.post("/{id}/update", response_model=Optional[EmailMailboxModel])
async def update_mailbox(
    id: str,
    form_data: EmailMailboxUpdateForm,
    user=Depends(get_verified_user),
):
    """Update a mailbox configuration"""
    mailbox = EmailMailboxes.get_mailbox_by_id(id)
    if not mailbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    if (
        mailbox.user_id != user.id
        and user.role != "admin"
        and not has_access(user.id, "write", mailbox.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )
    
    try:
        updated = EmailMailboxes.update_mailbox_by_id(id, form_data)
        return updated
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


############################
# Regenerate Webhook Token
############################


@router.post("/{id}/regenerate-token", response_model=dict)
async def regenerate_webhook_token(id: str, user=Depends(get_verified_user)):
    """Regenerate the webhook token for a mailbox"""
    mailbox = EmailMailboxes.get_mailbox_by_id(id)
    if not mailbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    if (
        mailbox.user_id != user.id
        and user.role != "admin"
        and not has_access(user.id, "write", mailbox.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )
    
    new_token = EmailMailboxes.regenerate_webhook_token(id)
    if not new_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to regenerate token",
        )
    
    return {"webhook_token": new_token}


############################
# Delete Mailbox
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_mailbox(id: str, user=Depends(get_verified_user)):
    """Delete a mailbox configuration"""
    mailbox = EmailMailboxes.get_mailbox_by_id(id)
    if not mailbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    if (
        mailbox.user_id != user.id
        and user.role != "admin"
        and not has_access(user.id, "write", mailbox.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )
    
    try:
        # Delete all emails associated with this mailbox
        EmailMessages.delete_emails_by_mailbox_id(id)
        # Delete the mailbox
        EmailMailboxes.delete_mailbox_by_id(id)
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


############################
# Get Emails by Mailbox
############################


@router.get("/{id}/emails", response_model=list[EmailMessageModel])
async def get_emails_by_mailbox(
    id: str,
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_verified_user),
):
    """Get emails received for a specific mailbox"""
    mailbox = EmailMailboxes.get_mailbox_by_id(id)
    if not mailbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    if mailbox.user_id != user.id and user.role != "admin":
        # Check if user has access to the channel
        channel = Channels.get_channel_by_id(mailbox.channel_id)
        if not channel or not has_access(
            user.id, type="read", access_control=channel.access_control
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )
    
    return EmailMessages.get_emails_by_mailbox_id(id, skip, limit)


############################
# Webhook - Receive Email from Power Automate
############################


async def process_email_with_agent(
    request: Request,
    mailbox: EmailMailboxModel,
    channel: ChannelModel,
    message: MessageModel,
    email_record: EmailMessageModel,
    user,
):
    """Process the email with AI agent and post response to channel"""
    if not mailbox.model_id:
        return
    
    try:
        MODELS = {
            model["id"]: model
            for model in get_filtered_models(await get_all_models(request, user=user), user)
        }
        
        model = MODELS.get(mailbox.model_id, None)
        if not model:
            log.warning(f"Model {mailbox.model_id} not found for email processing")
            return
        
        # Prepare email content for analysis
        email_data = email_record.data or {}
        email_content = f"""
New email received:

**From:** {email_record.sender_name or email_record.sender} <{email_record.sender}>
**Subject:** {email_record.subject}
**Importance:** {email_record.importance or 'normal'}
**Has Attachments:** {'Yes' if email_record.has_attachments else 'No'}

**Body:**
{email_data.get('body', email_record.body_preview or 'No content')}
"""
        
        # Create initial response message
        response_message = Messages.insert_new_message(
            MessageForm(
                content="",
                parent_id=message.id,
                meta={
                    "model_id": mailbox.model_id,
                    "model_name": model.get("name", mailbox.model_id),
                    "email_id": email_record.id,
                },
            ),
            channel.id,
            user.id,
        )
        
        if response_message:
            # Emit initial message
            await sio.emit(
                "events:channel",
                {
                    "channel_id": channel.id,
                    "message_id": response_message.id,
                    "data": {
                        "type": "message",
                        "data": response_message.model_dump(),
                    },
                    "user": UserNameResponse(**user.model_dump()).model_dump(),
                    "channel": channel.model_dump(),
                },
                to=f"channel:{channel.id}",
            )
        
        # Generate response with the model
        system_prompt = f"""You are {model.get('name', mailbox.model_id)}, an email assistant monitoring the mailbox {mailbox.mailbox_address}.

When you receive an email, analyze it and provide:
1. A brief summary of what the email is about
2. Any action items or requests identified
3. Suggested response or next steps
4. Priority assessment (urgent, high, normal, low)

Be concise and actionable in your analysis. If there are any calls to action (like calling someone, checking a file, scheduling a meeting), clearly highlight them.

Users can reply to ask follow-up questions about the email content."""

        form_data = {
            "model": mailbox.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": email_content},
            ],
            "stream": False,
        }
        
        res = await generate_chat_completion(
            request,
            form_data=form_data,
            user=user,
        )
        
        if res and response_message:
            content = ""
            if res.get("choices", []) and len(res["choices"]) > 0:
                content = res["choices"][0]["message"]["content"]
            elif res.get("error", None):
                content = f"Error analyzing email: {res['error']}"
            
            # Update the response message
            Messages.update_message_by_id(
                response_message.id,
                MessageForm(
                    content=content,
                    meta={"done": True},
                ),
            )
            
            # Emit update
            updated_message = Messages.get_message_by_id(response_message.id)
            if updated_message:
                await sio.emit(
                    "events:channel",
                    {
                        "channel_id": channel.id,
                        "message_id": response_message.id,
                        "data": {
                            "type": "message:update",
                            "data": updated_message.model_dump(),
                        },
                        "user": UserNameResponse(**user.model_dump()).model_dump(),
                        "channel": channel.model_dump(),
                    },
                    to=f"channel:{channel.id}",
                )
            
            # Update email record as processed
            EmailMessages.update_email_processed(
                email_record.id,
                processed=True,
                agent_response=content[:500] if content else None,
            )
    
    except Exception as e:
        log.exception(f"Error processing email with agent: {e}")


@router.post("/webhook/{token}", response_model=dict)
async def receive_email_webhook(
    request: Request,
    token: str,
    form_data: IncomingEmailForm,
    background_tasks: BackgroundTasks,
):
    """
    Webhook endpoint for Power Automate to send emails.
    
    Power Automate flow should:
    1. Trigger on new email in mailbox
    2. Send HTTP POST to: {base_url}/api/v1/emails/webhook/{webhook_token}
    3. Include email data in the request body
    
    Example Power Automate body:
    {
        "email_id": "@{triggerOutputs()?['body/id']}",
        "subject": "@{triggerOutputs()?['body/subject']}",
        "sender": "@{triggerOutputs()?['body/from']}",
        "sender_name": "@{triggerOutputs()?['body/from']}",
        "body": "@{triggerOutputs()?['body/body']}",
        "body_preview": "@{triggerOutputs()?['body/bodyPreview']}",
        "has_attachments": @{triggerOutputs()?['body/hasAttachments']},
        "received_at": "@{triggerOutputs()?['body/receivedDateTime']}",
        "importance": "@{triggerOutputs()?['body/importance']}"
    }
    """
    # Find mailbox by webhook token
    mailbox = EmailMailboxes.get_mailbox_by_webhook_token(token)
    if not mailbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid webhook token or mailbox inactive",
        )
    
    # Get the channel
    channel = Channels.get_channel_by_id(mailbox.channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated channel not found",
        )
    
    # Get the mailbox owner to post as
    owner = Users.get_user_by_id(mailbox.user_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mailbox owner not found",
        )
    
    try:
        # Create the email record
        email_record = EmailMessages.insert_new_email(
            mailbox_id=mailbox.id,
            channel_id=channel.id,
            form_data=form_data,
        )
        
        if not email_record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create email record",
            )
        
        # Format email content for channel message
        attachments_text = ""
        if form_data.has_attachments and form_data.attachments:
            attachments_text = "\n📎 **Attachments:** " + ", ".join(
                [a.get("name", "attachment") for a in form_data.attachments]
            )
        
        message_content = f"""📧 **New Email Received**

**From:** {form_data.sender_name or form_data.sender}
**Subject:** {form_data.subject or '(No subject)'}
**Importance:** {form_data.importance or 'normal'}{attachments_text}

---
{form_data.body_preview or form_data.body or '(No content)'}
"""
        
        # Create channel message
        message = Messages.insert_new_message(
            MessageForm(
                content=message_content,
                data={
                    "email_id": email_record.id,
                    "mailbox_id": mailbox.id,
                },
                meta={
                    "type": "email",
                    "email_id": email_record.id,
                    "from": form_data.sender,
                    "subject": form_data.subject,
                },
            ),
            channel.id,
            owner.id,
        )
        
        if message:
            # Update email record with message ID
            EmailMessages.update_email_message_id(email_record.id, message.id)
            
            # Emit to channel
            await sio.emit(
                "events:channel",
                {
                    "channel_id": channel.id,
                    "message_id": message.id,
                    "data": {
                        "type": "message",
                        "data": message.model_dump(),
                    },
                    "user": UserNameResponse(**owner.model_dump()).model_dump(),
                    "channel": channel.model_dump(),
                },
                to=f"channel:{channel.id}",
            )
            
            # Increment email count
            EmailMailboxes.increment_email_count(mailbox.id)
            
            # Process with AI agent in background
            if mailbox.model_id:
                background_tasks.add_task(
                    process_email_with_agent,
                    request,
                    mailbox,
                    channel,
                    message,
                    email_record,
                    owner,
                )
        
        return {
            "success": True,
            "email_id": email_record.id,
            "message_id": message.id if message else None,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


############################
# Get Webhook URL Info
############################


@router.get("/{id}/webhook-info", response_model=dict)
async def get_webhook_info(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
):
    """Get webhook URL and instructions for Power Automate setup"""
    mailbox = EmailMailboxes.get_mailbox_by_id(id)
    if not mailbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    if (
        mailbox.user_id != user.id
        and user.role != "admin"
        and not has_access(user.id, "read", mailbox.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )
    
    base_url = str(request.base_url).rstrip('/')
    webhook_url = f"{base_url}/api/v1/emails/webhook/{mailbox.webhook_token}"
    
    body_template = {
        "email_id": "@{triggerOutputs()?['body/id']}",
        "subject": "@{triggerOutputs()?['body/subject']}",
        "sender": "@{triggerOutputs()?['body/from']}",
        "sender_name": "@{triggerOutputs()?['body/from']}",
        "body": "@{triggerOutputs()?['body/body']}",
        "body_preview": "@{triggerOutputs()?['body/bodyPreview']}",
        "has_attachments": "@{triggerOutputs()?['body/hasAttachments']}",
        "received_at": "@{triggerOutputs()?['body/receivedDateTime']}",
        "importance": "@{triggerOutputs()?['body/importance']}",
    }
    body_template_text = json.dumps(body_template, indent=2)

    return {
        "webhook_url": webhook_url,
        "webhook_token": mailbox.webhook_token,
        "instructions": {
            "title": "Power Automate Setup Instructions",
            "steps": [
                "1. Create a new Flow in Power Automate",
                "2. Select trigger: 'When a new email arrives (V3)' from Office 365 Outlook",
                f"3. Configure the trigger for mailbox: {mailbox.mailbox_address}",
                "4. Add action: 'HTTP' and configure as POST request",
                f"5. Set URL to: {webhook_url}",
                "6. Set Content-Type header to: application/json",
                "7. Use the following body template (copy and customize):",
            ],
            "body_template": body_template,
            "body_template_text": body_template_text,
        },
    }

