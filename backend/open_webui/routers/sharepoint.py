import logging
import time
import uuid
import os
import io
import asyncio
import functools
import httpx
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
import mimetypes

from open_webui.models.sharepoint_sync import (
    SharePointSyncs,
    SharePointSyncForm,
    SharePointSyncModel,
    SharePointSyncUpdateForm,
)
from open_webui.models.knowledge import Knowledges
from open_webui.models.files import Files, FileForm

from open_webui.routers.retrieval import process_file, ProcessFileForm
from open_webui.storage.provider import Storage

from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_access

from open_webui.env import SRC_LOG_LEVELS
from open_webui.config import UPLOAD_DIR

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


############################
# Get SharePoint Syncs
############################


@router.get("/", response_model=List[SharePointSyncModel])
async def get_sharepoint_syncs(user=Depends(get_verified_user)):
    """Get all SharePoint syncs the user has access to (or all for admin)"""
    if user.role == "admin":
        return SharePointSyncs.get_all_syncs()
    return SharePointSyncs.get_syncs_by_user_id(user.id, permission="read")


############################
# Get SharePoint Sync by ID
############################


@router.get("/{id}", response_model=Optional[SharePointSyncModel])
async def get_sharepoint_sync_by_id(id: str, user=Depends(get_verified_user)):
    """Get a specific SharePoint sync by ID"""
    sync = SharePointSyncs.get_sync_by_id(id)

    if not sync:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check access: owner, admin, or has read permission
    if sync.user_id != user.id and user.role != "admin":
        if not SharePointSyncs.has_access_to_sync(id, user.id, "read"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )

    return sync


############################
# Create SharePoint Sync
############################


@router.post("/create", response_model=Optional[SharePointSyncModel])
async def create_sharepoint_sync(
    form_data: SharePointSyncForm, user=Depends(get_verified_user)
):
    """Create a new SharePoint sync configuration"""
    # Verify user has access to the knowledge base
    knowledge = Knowledges.get_knowledge_by_id(id=form_data.knowledge_id)

    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    if knowledge.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    sync = SharePointSyncs.insert_new_sync(user.id, form_data)

    if not sync:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create SharePoint sync",
        )

    return sync


############################
# Update SharePoint Sync
############################


class SharePointSyncUpdateRequest(BaseModel):
    name: Optional[str] = None
    access_control: Optional[dict] = None


@router.post("/{id}/update", response_model=Optional[SharePointSyncModel])
async def update_sharepoint_sync(
    id: str, form_data: SharePointSyncUpdateRequest, user=Depends(get_verified_user)
):
    """Update a SharePoint sync configuration (name, access_control)"""
    sync = SharePointSyncs.get_sync_by_id(id)

    if not sync:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Only owner or admin can update access control
    if sync.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    updated = SharePointSyncs.update_sync_by_id(
        id,
        SharePointSyncUpdateForm(
            name=form_data.name,
            access_control=form_data.access_control,
        ),
    )

    return updated


############################
# Cancel SharePoint Sync
############################


@router.post("/{id}/cancel")
async def cancel_sharepoint_sync(id: str, user=Depends(get_verified_user)):
    """Cancel a running SharePoint sync"""
    sync = SharePointSyncs.get_sync_by_id(id)

    if not sync:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check access: owner, admin, or has write permission
    if sync.user_id != user.id and user.role != "admin":
        if not SharePointSyncs.has_access_to_sync(id, user.id, "write"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )

    if sync.sync_status != "syncing":
        return {"status": False, "message": "Sync is not running"}

    # Mark as cancelled
    SharePointSyncs.update_sync_by_id(
        id,
        SharePointSyncUpdateForm(
            sync_status="cancelled",
            sync_error="Sync was cancelled by user",
        ),
    )

    return {"status": True, "message": "Sync cancelled"}


############################
# Delete SharePoint Sync
############################


@router.delete("/{id}")
async def delete_sharepoint_sync(id: str, user=Depends(get_verified_user)):
    """Delete a SharePoint sync configuration"""
    sync = SharePointSyncs.get_sync_by_id(id)

    if not sync:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check access: owner, admin, or has write permission
    if sync.user_id != user.id and user.role != "admin":
        if not SharePointSyncs.has_access_to_sync(id, user.id, "write"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )

    result = SharePointSyncs.delete_sync_by_id(id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete SharePoint sync",
        )

    return {"status": True}


############################
# Execute SharePoint Sync
############################


class SyncExecuteForm(BaseModel):
    access_token: str


class TokenExpiredError(Exception):
    """Raised when the SharePoint access token has expired"""
    pass


async def retry_request(client, method: str, url: str, max_retries: int = 3, **kwargs):
    """Make an HTTP request with retry logic for transient SharePoint errors"""
    last_error = None
    for attempt in range(max_retries):
        try:
            if method == "GET":
                response = await client.get(url, **kwargs)
            else:
                response = await client.post(url, **kwargs)
            
            # Check for expired token error (don't retry - need user to re-authenticate)
            if response.status_code == 401:
                try:
                    error_data = response.json()
                    error_code = error_data.get("error", {}).get("code", "")
                    inner_code = error_data.get("error", {}).get("innerError", {}).get("code", "")
                    if "expired" in error_code.lower() or "expired" in inner_code.lower() or error_code == "unauthenticated":
                        raise TokenExpiredError("Access token has expired. Please click Sync again to re-authenticate.")
                except (ValueError, KeyError):
                    pass
                raise TokenExpiredError("Authentication failed. Please click Sync again to re-authenticate.")
            
            # Check if SharePoint returned an HTML error page
            content_type = response.headers.get("content-type", "")
            if response.status_code == 200 and "text/html" in content_type:
                # SharePoint returned an error page, retry
                log.warning(f"SharePoint returned HTML error page, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    continue
                raise Exception("SharePoint returned HTML error page after all retries")
            
            return response
        except TokenExpiredError:
            # Don't retry token expiry errors
            raise
        except httpx.TimeoutException as e:
            last_error = e
            log.warning(f"Request timeout, attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                raise
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                raise
    raise last_error


async def download_file_from_sharepoint(
    endpoint: str, drive_id: str, item_id: str, access_token: str
) -> tuple[bytes, str, str]:
    """Download a file from SharePoint and return its content, name, and content type"""
    async with httpx.AsyncClient() as client:
        # Get file metadata first with retry
        metadata_url = f"{endpoint}/drives/{drive_id}/items/{item_id}"
        metadata_response = await retry_request(
            client, "GET", metadata_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=60.0,
        )

        if metadata_response.status_code != 200:
            raise Exception(f"Failed to get file metadata: {metadata_response.text}")

        file_metadata = metadata_response.json()
        file_name = file_metadata.get("name", "unknown")
        download_url = file_metadata.get("@microsoft.graph.downloadUrl") or file_metadata.get("@content.downloadUrl")

        if not download_url:
            raise Exception("Download URL not found in file metadata")

        # Download the file with retry
        download_response = await retry_request(
            client, "GET", download_url, 
            timeout=300.0,
            max_retries=3
        )

        if download_response.status_code != 200:
            raise Exception(f"Failed to download file: {download_response.text}")

        content_type = download_response.headers.get(
            "content-type", "application/octet-stream"
        )

        return download_response.content, file_name, content_type


async def list_folder_contents(
    endpoint: str, drive_id: str, item_id: str, access_token: str
) -> List[dict]:
    """List all files in a SharePoint folder recursively"""
    files = []

    async with httpx.AsyncClient() as client:
        # Get folder children
        children_url = f"{endpoint}/drives/{drive_id}/items/{item_id}/children"

        while children_url:
            response = await retry_request(
                client, "GET", children_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=60.0,
            )

            if response.status_code != 200:
                raise Exception(f"Failed to list folder contents: {response.text}")

            data = response.json()
            items = data.get("value", [])

            for item in items:
                if item.get("folder"):
                    # Recursively get files from subfolders
                    subfolder_files = await list_folder_contents(
                        endpoint, drive_id, item["id"], access_token
                    )
                    files.extend(subfolder_files)
                elif item.get("file"):
                    files.append(
                        {
                            "id": item["id"],
                            "name": item["name"],
                            "size": item.get("size", 0),
                            "lastModifiedDateTime": item.get("lastModifiedDateTime"),
                            "mimeType": item.get("file", {}).get("mimeType", "application/octet-stream"),
                            "parentPath": item.get("parentReference", {}).get("path", ""),
                        }
                    )

            # Handle pagination
            children_url = data.get("@odata.nextLink")

    return files


def get_existing_sharepoint_files(sync_id: str) -> dict:
    """Get a map of SharePoint item IDs to file IDs for files already synced"""
    from open_webui.internal.db import get_db
    from open_webui.models.files import File
    
    existing = {}
    with get_db() as db:
        # Query all files and check meta for sharepoint_sync_id
        files = db.query(File).all()
        for file in files:
            if file.meta and isinstance(file.meta, dict):
                if file.meta.get("sharepoint_sync_id") == sync_id:
                    sp_item_id = file.meta.get("sharepoint_item_id")
                    if sp_item_id:
                        existing[sp_item_id] = {
                            "file_id": file.id,
                            "last_modified": file.meta.get("sharepoint_last_modified"),
                        }
    return existing


def add_sync_log(sync_id: str, level: str, message: str, file_name: str = None):
    """Add a log entry to the sync's log list"""
    sync = SharePointSyncs.get_sync_by_id(sync_id)
    if sync:
        logs = sync.sync_logs or []
        logs.append({
            "timestamp": int(time.time()),
            "level": level,  # info, warning, error, success
            "message": message,
            "file_name": file_name,
        })
        # Keep only last 100 logs to avoid DB bloat
        if len(logs) > 100:
            logs = logs[-100:]
        SharePointSyncs.update_sync_by_id(sync_id, SharePointSyncUpdateForm(sync_logs=logs))


async def run_sync_in_background(
    sync_id: str,
    user_id: str,
    access_token: str,
    sharepoint_endpoint: str,
    drive_id: str,
    item_id: str,
    knowledge_id: str,
):
    """Background task to run SharePoint sync"""
    import asyncio
    
    try:
        # Clear previous logs and start fresh
        SharePointSyncs.update_sync_by_id(sync_id, SharePointSyncUpdateForm(sync_logs=[]))
        add_sync_log(sync_id, "info", "Sync started")

        # Get existing synced files to avoid duplicates
        existing_files = get_existing_sharepoint_files(sync_id)
        log.info(f"[Sync {sync_id}] Found {len(existing_files)} existing synced files")
        add_sync_log(sync_id, "info", f"Found {len(existing_files)} existing synced files")

        # Get all files in the SharePoint folder
        files = await list_folder_contents(
            sharepoint_endpoint,
            drive_id,
            item_id,
            access_token,
        )

        log.info(f"[Sync {sync_id}] Found {len(files)} files in SharePoint folder")
        add_sync_log(sync_id, "info", f"Found {len(files)} files in SharePoint folder")
        
        # Set total files count for progress tracking
        total_files = len(files)
        SharePointSyncs.update_sync_by_id(
            sync_id, 
            SharePointSyncUpdateForm(sync_total=total_files, sync_progress=0)
        )

        synced_count = 0
        skipped_count = 0
        errors = []
        current_progress = 0

        for sp_file in files:
            try:
                # Check if sync was cancelled
                current_sync = SharePointSyncs.get_sync_by_id(sync_id)
                if current_sync and current_sync.sync_status == "cancelled":
                    log.info(f"[Sync {sync_id}] Sync was cancelled by user")
                    add_sync_log(sync_id, "info", "Sync cancelled by user")
                    return  # Exit the sync loop
                
                sp_item_id = sp_file["id"]
                sp_last_modified = sp_file.get("lastModifiedDateTime")
                file_name = sp_file.get("name", "unknown")
                
                # Update progress
                current_progress += 1
                SharePointSyncs.update_sync_by_id(
                    sync_id, 
                    SharePointSyncUpdateForm(sync_progress=current_progress)
                )
                
                # Check if file already exists
                if sp_item_id in existing_files:
                    existing = existing_files[sp_item_id]
                    # Skip if file hasn't been modified
                    if existing["last_modified"] == sp_last_modified:
                        skipped_count += 1
                        log.debug(f"[Sync {sync_id}] Skipping unchanged file: {file_name}")
                        add_sync_log(sync_id, "skip", f"Skipped (unchanged)", file_name)
                        continue
                    # TODO: Could update existing file if modified, for now just skip
                    log.info(f"[Sync {sync_id}] File modified but skipping update: {file_name}")
                    skipped_count += 1
                    add_sync_log(sync_id, "skip", f"Skipped (already exists)", file_name)
                    continue

                # Download the file (only for new files)
                content, file_name, content_type = await download_file_from_sharepoint(
                    sharepoint_endpoint,
                    drive_id,
                    sp_item_id,
                    access_token,
                )

                # Create a unique file ID
                file_id = str(uuid.uuid4())

                # Determine file extension
                _, file_extension = os.path.splitext(file_name)
                file_extension = file_extension[1:] if file_extension else ""

                # Save file to storage
                file_io = io.BytesIO(content)
                _, file_path = Storage.upload_file(file_io, file_name, {})

                # Create file record in database
                file_meta = {
                    "name": file_name,
                    "content_type": content_type,
                    "size": len(content),
                    "sharepoint_item_id": sp_item_id,
                    "sharepoint_drive_id": drive_id,
                    "sharepoint_sync_id": sync_id,
                    "sharepoint_last_modified": sp_last_modified,
                    "sharepoint_parent_path": sp_file.get("parentPath", ""),
                }

                file_item = Files.insert_new_file(
                    user_id,
                    FileForm(
                        id=file_id,
                        filename=file_name,
                        path=file_path,
                        meta=file_meta,
                    ),
                )

                if file_item:
                    # Add file to knowledge base (skip RAG processing in background for speed)
                    try:
                        knowledge = Knowledges.add_file_to_knowledge_by_id(
                            knowledge_id, file_item.id, user_id
                        )
                        if knowledge:
                            synced_count += 1
                            log.info(f"[Sync {sync_id}] Synced new file: {file_name}")
                            add_sync_log(sync_id, "success", "Synced successfully", file_name)
                        else:
                            errors.append(f"Failed to add {file_name} to knowledge base")
                            add_sync_log(sync_id, "error", "Failed to add to knowledge base", file_name)
                    except Exception as e:
                        log.error(f"[Sync {sync_id}] Error adding file to knowledge: {e}")
                        errors.append(f"Failed to add {file_name}: {str(e)}")
                        add_sync_log(sync_id, "error", f"Error: {str(e)[:100]}", file_name)
                else:
                    errors.append(f"Failed to create file record for {file_name}")
                    add_sync_log(sync_id, "error", "Failed to create file record", file_name)

            except Exception as e:
                log.error(f"[Sync {sync_id}] Error syncing file {sp_file.get('name')}: {e}")
                errors.append(f"Error syncing {sp_file.get('name')}: {str(e)}")
                add_sync_log(sync_id, "error", f"Error: {str(e)[:100]}", sp_file.get('name'))

        # Update sync status to completed
        sync_error = "; ".join(errors[:5]) if errors else None  # Limit error message length
        total_files = synced_count + skipped_count  # Total files in sync
        
        # Add completion log
        completion_msg = f"Completed: {synced_count} new, {skipped_count} skipped, {len(errors)} errors"
        add_sync_log(sync_id, "info", completion_msg)
        
        SharePointSyncs.update_sync_by_id(
            sync_id,
            SharePointSyncUpdateForm(
                sync_status="synced" if not errors else "error",
                sync_error=sync_error,
                last_sync_at=int(time.time()),
                file_count=total_files,
            ),
        )
        log.info(f"[Sync {sync_id}] {completion_msg}")

    except TokenExpiredError as e:
        log.warning(f"[Sync {sync_id}] Token expired during sync")
        add_sync_log(sync_id, "error", "Token expired - please click Sync to re-authenticate")
        SharePointSyncs.update_sync_by_id(
            sync_id,
            SharePointSyncUpdateForm(
                sync_status="token_expired",
                sync_error="Access token expired. Please click Sync again to re-authenticate.",
            ),
        )
    except Exception as e:
        log.error(f"[Sync {sync_id}] Background sync failed: {e}")
        add_sync_log(sync_id, "error", f"Sync failed: {str(e)[:200]}")
        SharePointSyncs.update_sync_by_id(
            sync_id,
            SharePointSyncUpdateForm(
                sync_status="error",
                sync_error=str(e),
            ),
        )


@router.post("/{id}/sync")
async def execute_sharepoint_sync(
    request: Request,
    id: str,
    form_data: SyncExecuteForm,
    background_tasks: BackgroundTasks,
    user=Depends(get_verified_user),
):
    """Start a SharePoint sync in the background - returns immediately"""
    sync = SharePointSyncs.get_sync_by_id(id)

    if not sync:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check access: owner, admin, or has write permission
    if sync.user_id != user.id and user.role != "admin":
        if not SharePointSyncs.has_access_to_sync(id, user.id, "write"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )

    # Check if already syncing
    if sync.sync_status == "syncing":
        return {
            "status": True,
            "message": "Sync already in progress",
            "sync_status": "syncing",
        }

    # Update status to syncing immediately and reset progress
    SharePointSyncs.update_sync_by_id(
        id, SharePointSyncUpdateForm(
            sync_status="syncing", 
            sync_error=None,
            sync_progress=0,
            sync_total=0
        )
    )

    # Add background task - runs after response is sent
    background_tasks.add_task(
        run_sync_in_background,
        sync_id=id,
        user_id=user.id,
        access_token=form_data.access_token,
        sharepoint_endpoint=sync.sharepoint_endpoint,
        drive_id=sync.drive_id,
        item_id=sync.item_id,
        knowledge_id=sync.knowledge_id,
    )

    return {
        "status": True,
        "message": "Sync started in background",
        "sync_status": "syncing",
    }


@router.get("/{id}/status")
async def get_sync_status(
    id: str,
    user=Depends(get_verified_user),
):
    """Get the current status of a SharePoint sync"""
    sync = SharePointSyncs.get_sync_by_id(id)

    if not sync:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check access: owner, admin, or has read permission
    if sync.user_id != user.id and user.role != "admin":
        if not SharePointSyncs.has_access_to_sync(id, user.id, "read"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )

    return SharePointSyncModel.model_validate(sync)


############################
# List SharePoint Folder Contents (Preview)
############################


class ListFolderForm(BaseModel):
    access_token: str
    endpoint: str
    drive_id: str
    item_id: str


@router.post("/list-folder")
async def list_sharepoint_folder(
    form_data: ListFolderForm, user=Depends(get_verified_user)
):
    """List contents of a SharePoint folder for preview"""
    try:
        files = await list_folder_contents(
            form_data.endpoint,
            form_data.drive_id,
            form_data.item_id,
            form_data.access_token,
        )
        return {"files": files, "count": len(files)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

