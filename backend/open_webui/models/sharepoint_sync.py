import logging
import time
from typing import Optional, List
import uuid

from open_webui.internal.db import Base, get_db

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text
from open_webui.internal.db import JSONField

from open_webui.utils.access_control import has_access
from open_webui.models.groups import Groups

log = logging.getLogger(__name__)

####################
# SharePointSync DB Schema
####################


class SharePointSync(Base):
    __tablename__ = "sharepoint_sync"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    name = Column(Text)  # Display name for the sync
    knowledge_id = Column(Text)  # Target knowledge collection ID

    # SharePoint folder info
    drive_id = Column(Text)
    item_id = Column(Text)  # Folder item ID
    folder_path = Column(Text)  # Display path
    sharepoint_endpoint = Column(Text)  # The SharePoint endpoint URL

    # Sync metadata
    last_sync_at = Column(BigInteger, nullable=True)
    file_count = Column(BigInteger, default=0)
    sync_status = Column(Text, default="idle")  # idle, syncing, synced, error
    sync_error = Column(Text, nullable=True)
    sync_logs = Column(JSONField, nullable=True)  # List of log entries
    sync_progress = Column(BigInteger, default=0)  # Current file being processed
    sync_total = Column(BigInteger, default=0)  # Total files to process

    access_control = Column(JSONField, nullable=True)  # Controls data access levels
    # - `None`: Public access, available to all users with the "user" role.
    # - `{}`: Private access, only accessible by the owner.
    # - `{"read": {"group_ids": ["group_id"]}}`: Read access for specific groups

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class SharePointSyncModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: Optional[str] = ""  # Allow None, default to empty string
    knowledge_id: str

    drive_id: str
    item_id: str
    folder_path: str
    sharepoint_endpoint: str

    last_sync_at: Optional[int] = None
    file_count: int = 0
    sync_status: str = "idle"
    sync_error: Optional[str] = None
    sync_logs: Optional[List[dict]] = None
    sync_progress: int = 0
    sync_total: int = 0

    access_control: Optional[dict] = None

    created_at: int
    updated_at: int


####################
# Forms
####################


class SharePointSyncForm(BaseModel):
    name: str
    knowledge_id: str
    drive_id: str
    item_id: str
    folder_path: str
    sharepoint_endpoint: str
    access_control: Optional[dict] = None


class SharePointSyncUpdateForm(BaseModel):
    name: Optional[str] = None
    last_sync_at: Optional[int] = None
    file_count: Optional[int] = None
    sync_status: Optional[str] = None
    sync_error: Optional[str] = None
    sync_logs: Optional[List[dict]] = None
    sync_progress: Optional[int] = None
    sync_total: Optional[int] = None
    access_control: Optional[dict] = None


####################
# SharePointSyncs Table
####################


class SharePointSyncsTable:
    def insert_new_sync(
        self, user_id: str, form_data: SharePointSyncForm
    ) -> Optional[SharePointSyncModel]:
        with get_db() as db:
            sync_id = str(uuid.uuid4())
            sync = SharePointSyncModel(
                id=sync_id,
                user_id=user_id,
                name=form_data.name,
                knowledge_id=form_data.knowledge_id,
                drive_id=form_data.drive_id,
                item_id=form_data.item_id,
                folder_path=form_data.folder_path,
                sharepoint_endpoint=form_data.sharepoint_endpoint,
                last_sync_at=None,
                file_count=0,
                sync_status="idle",
                sync_error=None,
                access_control=form_data.access_control,
                created_at=int(time.time()),
                updated_at=int(time.time()),
            )

            try:
                result = SharePointSync(**sync.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return SharePointSyncModel.model_validate(result)
                return None
            except Exception as e:
                log.exception(f"Error creating SharePoint sync: {e}")
                return None

    def get_sync_by_id(self, id: str) -> Optional[SharePointSyncModel]:
        with get_db() as db:
            try:
                sync = db.query(SharePointSync).filter_by(id=id).first()
                if sync:
                    return SharePointSyncModel.model_validate(sync)
                return None
            except Exception:
                return None

    def get_all_syncs(self) -> List[SharePointSyncModel]:
        """Get all syncs (admin only)"""
        with get_db() as db:
            try:
                syncs = (
                    db.query(SharePointSync)
                    .order_by(SharePointSync.updated_at.desc())
                    .all()
                )
                return [SharePointSyncModel.model_validate(sync) for sync in syncs]
            except Exception as e:
                log.exception(f"Error getting all syncs: {e}")
                return []

    def get_syncs_by_user_id(
        self, user_id: str, permission: str = "read"
    ) -> List[SharePointSyncModel]:
        """Get all syncs that a user has access to (owned or has permission)"""
        with get_db() as db:
            try:
                syncs = (
                    db.query(SharePointSync)
                    .order_by(SharePointSync.updated_at.desc())
                    .all()
                )
                user_group_ids = {
                    group.id for group in Groups.get_groups_by_member_id(user_id)
                }
                return [
                    SharePointSyncModel.model_validate(sync)
                    for sync in syncs
                    if sync.user_id == user_id
                    or has_access(user_id, permission, sync.access_control, user_group_ids)
                ]
            except Exception as e:
                log.exception(f"Error getting syncs for user {user_id}: {e}")
                return []

    def has_access_to_sync(
        self, sync_id: str, user_id: str, permission: str = "read"
    ) -> bool:
        """Check if a user has access to a specific sync"""
        sync = self.get_sync_by_id(sync_id)
        if not sync:
            return False
        if sync.user_id == user_id:
            return True
        user_group_ids = {
            group.id for group in Groups.get_groups_by_member_id(user_id)
        }
        return has_access(user_id, permission, sync.access_control, user_group_ids)

    def get_syncs_by_knowledge_id(self, knowledge_id: str) -> List[SharePointSyncModel]:
        with get_db() as db:
            try:
                syncs = (
                    db.query(SharePointSync)
                    .filter_by(knowledge_id=knowledge_id)
                    .order_by(SharePointSync.updated_at.desc())
                    .all()
                )
                return [SharePointSyncModel.model_validate(sync) for sync in syncs]
            except Exception:
                return []

    def update_sync_by_id(
        self, id: str, form_data: SharePointSyncUpdateForm
    ) -> Optional[SharePointSyncModel]:
        with get_db() as db:
            try:
                sync = db.query(SharePointSync).filter_by(id=id).first()
                if sync:
                    update_data = form_data.model_dump(exclude_unset=True)
                    update_data["updated_at"] = int(time.time())
                    for key, value in update_data.items():
                        setattr(sync, key, value)
                    db.commit()
                    db.refresh(sync)
                    return SharePointSyncModel.model_validate(sync)
                return None
            except Exception as e:
                log.exception(f"Error updating SharePoint sync: {e}")
                return None

    def delete_sync_by_id(self, id: str) -> bool:
        with get_db() as db:
            try:
                sync = db.query(SharePointSync).filter_by(id=id).first()
                if sync:
                    db.delete(sync)
                    db.commit()
                    return True
                return False
            except Exception as e:
                log.exception(f"Error deleting SharePoint sync: {e}")
                return False


SharePointSyncs = SharePointSyncsTable()


# Auto-create table and ensure columns exist
def ensure_sharepoint_sync_table():
    """Create the sharepoint_sync table if it doesn't exist, and add missing columns"""
    from open_webui.internal.db import engine
    from sqlalchemy import inspect, text
    
    try:
        # Create table if it doesn't exist
        SharePointSync.__table__.create(engine, checkfirst=True)
        log.info("SharePoint sync table ready")
        
        # Check for missing columns and add them
        inspector = inspect(engine)
        if inspector.has_table("sharepoint_sync"):
            existing_columns = {col["name"] for col in inspector.get_columns("sharepoint_sync")}
            
            # Define columns that might be missing (added in updates)
            columns_to_check = {
                "sync_logs": "TEXT",  # JSON stored as TEXT
                "sync_progress": "INTEGER DEFAULT 0",
                "sync_total": "INTEGER DEFAULT 0",
                "access_control": "TEXT",  # JSON stored as TEXT
            }
            
            with engine.connect() as conn:
                for col_name, col_type in columns_to_check.items():
                    if col_name not in existing_columns:
                        try:
                            conn.execute(text(f"ALTER TABLE sharepoint_sync ADD COLUMN {col_name} {col_type}"))
                            conn.commit()
                            log.info(f"Added missing column '{col_name}' to sharepoint_sync table")
                        except Exception as col_err:
                            log.warning(f"Could not add column {col_name}: {col_err}")
                            
    except Exception as e:
        log.warning(f"Could not setup sharepoint_sync table: {e}")


# Run on module load
ensure_sharepoint_sync_table()

