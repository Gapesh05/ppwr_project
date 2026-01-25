# document_access_control.py
"""
Document Access Control Module

Implements role-based access control (RBAC) for supplier declaration documents
with fine-grained permissions and audit logging.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentRole(Enum):
    """User roles for document access"""
    ADMIN = "admin"
    MANAGER = "manager"
    VIEWER = "viewer"
    UPLOADER = "uploader"
    AUDITOR = "auditor"
    GUEST = "guest"


class DocumentPermission(Enum):
    """Fine-grained document permissions"""
    # Document operations
    UPLOAD = "upload"
    DOWNLOAD = "download"
    DELETE = "delete"
    ARCHIVE = "archive"
    RESTORE = "restore"
    
    # Metadata operations
    VIEW_METADATA = "view_metadata"
    EDIT_METADATA = "edit_metadata"
    
    # Access control
    GRANT_ACCESS = "grant_access"
    REVOKE_ACCESS = "revoke_access"
    
    # Audit operations
    VIEW_AUDIT_LOG = "view_audit_log"
    
    # Share operations
    SHARE_DOCUMENT = "share_document"


class RolePermissionMatrix:
    """Define role-based permissions"""
    
    ROLE_PERMISSIONS = {
        DocumentRole.ADMIN: [
            DocumentPermission.UPLOAD,
            DocumentPermission.DOWNLOAD,
            DocumentPermission.DELETE,
            DocumentPermission.ARCHIVE,
            DocumentPermission.RESTORE,
            DocumentPermission.VIEW_METADATA,
            DocumentPermission.EDIT_METADATA,
            DocumentPermission.GRANT_ACCESS,
            DocumentPermission.REVOKE_ACCESS,
            DocumentPermission.VIEW_AUDIT_LOG,
            DocumentPermission.SHARE_DOCUMENT,
        ],
        DocumentRole.MANAGER: [
            DocumentPermission.UPLOAD,
            DocumentPermission.DOWNLOAD,
            DocumentPermission.ARCHIVE,
            DocumentPermission.VIEW_METADATA,
            DocumentPermission.EDIT_METADATA,
            DocumentPermission.VIEW_AUDIT_LOG,
            DocumentPermission.SHARE_DOCUMENT,
        ],
        DocumentRole.UPLOADER: [
            DocumentPermission.UPLOAD,
            DocumentPermission.VIEW_METADATA,
        ],
        DocumentRole.VIEWER: [
            DocumentPermission.DOWNLOAD,
            DocumentPermission.VIEW_METADATA,
        ],
        DocumentRole.AUDITOR: [
            DocumentPermission.VIEW_METADATA,
            DocumentPermission.VIEW_AUDIT_LOG,
            DocumentPermission.DOWNLOAD,
        ],
        DocumentRole.GUEST: [],
    }


class AccessControlList:
    """
    Access Control List (ACL) for individual documents.
    
    Maintains fine-grained access control for each document.
    """
    
    def __init__(self, document_id: str, owner: str):
        """
        Initialize ACL.
        
        Args:
            document_id: Unique document identifier
            owner: User ID of document owner
        """
        self.document_id = document_id
        self.owner = owner
        self.permissions: Dict[str, List[DocumentPermission]] = {}
        self.created_at = datetime.utcnow()
        self.last_modified = datetime.utcnow()
    
    def grant_permission(
        self,
        user_id: str,
        permissions: List[DocumentPermission],
        granted_by: str
    ) -> bool:
        """
        Grant specific permissions to a user.
        
        Args:
            user_id: User ID to grant access to
            permissions: List of permissions to grant
            granted_by: User ID of person granting access
            
        Returns:
            True if successful
        """
        try:
            existing = self.permissions.get(user_id, [])
            new_permissions = list(set(existing + permissions))
            self.permissions[user_id] = new_permissions
            self.last_modified = datetime.utcnow()
            
            logger.info(
                f"Granted permissions to {user_id} for document {self.document_id} "
                f"by {granted_by}"
            )
            return True
        except Exception as e:
            logger.error(f"Error granting permission: {e}")
            return False
    
    def revoke_permission(
        self,
        user_id: str,
        permissions: List[DocumentPermission],
        revoked_by: str
    ) -> bool:
        """
        Revoke specific permissions from a user.
        
        Args:
            user_id: User ID to revoke access from
            permissions: List of permissions to revoke
            revoked_by: User ID of person revoking access
            
        Returns:
            True if successful
        """
        try:
            if user_id not in self.permissions:
                return False
            
            remaining = [
                p for p in self.permissions[user_id]
                if p not in permissions
            ]
            
            if remaining:
                self.permissions[user_id] = remaining
            else:
                del self.permissions[user_id]
            
            self.last_modified = datetime.utcnow()
            
            logger.info(
                f"Revoked permissions from {user_id} for document {self.document_id} "
                f"by {revoked_by}"
            )
            return True
        except Exception as e:
            logger.error(f"Error revoking permission: {e}")
            return False
    
    def has_permission(
        self,
        user_id: str,
        permission: DocumentPermission
    ) -> bool:
        """
        Check if user has specific permission.
        
        Args:
            user_id: User ID to check
            permission: Permission to verify
            
        Returns:
            True if user has permission
        """
        # Owner has all permissions
        if user_id == self.owner:
            return True
        
        return permission in self.permissions.get(user_id, [])
    
    def get_user_permissions(self, user_id: str) -> List[DocumentPermission]:
        """Get all permissions for a user"""
        if user_id == self.owner:
            return list(DocumentPermission)
        
        return self.permissions.get(user_id, [])
    
    def get_all_access(self) -> Dict[str, List[DocumentPermission]]:
        """Get all user access entries"""
        return {
            'owner': self.owner,
            'permissions': self.permissions,
            'created_at': self.created_at.isoformat(),
            'last_modified': self.last_modified.isoformat()
        }


class DocumentAccessController:
    """
    Central access control system for documents.
    
    Manages user roles, ACLs, and permission enforcement.
    """
    
    def __init__(self):
        """Initialize access controller"""
        self.acls: Dict[str, AccessControlList] = {}
        self.user_roles: Dict[str, DocumentRole] = {}
    
    def assign_role(self, user_id: str, role: DocumentRole):
        """Assign a role to a user"""
        self.user_roles[user_id] = role
        logger.info(f"Assigned role {role.value} to user {user_id}")
    
    def get_user_role(self, user_id: str) -> DocumentRole:
        """Get user's role"""
        return self.user_roles.get(user_id, DocumentRole.GUEST)
    
    def can_perform_action(
        self,
        user_id: str,
        permission: DocumentPermission,
        document_id: Optional[str] = None
    ) -> bool:
        """
        Check if user can perform an action.
        
        Uses both role-based permissions and document-specific ACLs.
        
        Args:
            user_id: User ID
            permission: Required permission
            document_id: Document ID (for ACL check)
            
        Returns:
            True if user has permission
        """
        # Get user's role
        role = self.get_user_role(user_id)
        
        # Check role-based permissions
        role_permissions = RolePermissionMatrix.ROLE_PERMISSIONS[role]
        if permission not in role_permissions:
            logger.warning(
                f"User {user_id} (role: {role.value}) lacks {permission.value} permission"
            )
            return False
        
        # Check document-specific ACL if document_id provided
        if document_id and document_id in self.acls:
            acl = self.acls[document_id]
            if not acl.has_permission(user_id, permission):
                logger.warning(
                    f"User {user_id} lacks ACL permission {permission.value} "
                    f"for document {document_id}"
                )
                return False
        
        logger.info(f"User {user_id} authorized for {permission.value}")
        return True
    
    def create_document_acl(
        self,
        document_id: str,
        owner: str
    ) -> AccessControlList:
        """Create ACL for new document"""
        acl = AccessControlList(document_id, owner)
        self.acls[document_id] = acl
        logger.info(f"Created ACL for document {document_id}, owner: {owner}")
        return acl
    
    def get_document_acl(self, document_id: str) -> Optional[AccessControlList]:
        """Get document's ACL"""
        return self.acls.get(document_id)
    
    def share_document(
        self,
        document_id: str,
        shared_with: str,
        permissions: List[DocumentPermission],
        shared_by: str
    ) -> bool:
        """
        Share document with another user.
        
        Args:
            document_id: Document to share
            shared_with: User to share with
            permissions: Permissions to grant
            shared_by: User sharing the document
            
        Returns:
            True if successful
        """
        # Verify sharer has share permission
        if not self.can_perform_action(shared_by, DocumentPermission.SHARE_DOCUMENT, document_id):
            logger.error(f"User {shared_by} not authorized to share document {document_id}")
            return False
        
        # Get or create ACL
        if document_id not in self.acls:
            logger.error(f"Document {document_id} not found")
            return False
        
        acl = self.acls[document_id]
        acl.grant_permission(shared_with, permissions, shared_by)
        
        logger.info(
            f"Document {document_id} shared with {shared_with} by {shared_by}"
        )
        return True
    
    def revoke_access(
        self,
        document_id: str,
        user_id: str,
        revoked_by: str
    ) -> bool:
        """
        Revoke all access to document from a user.
        
        Args:
            document_id: Document ID
            user_id: User to revoke access from
            revoked_by: User revoking access
            
        Returns:
            True if successful
        """
        # Verify revoker has permission
        if not self.can_perform_action(revoked_by, DocumentPermission.REVOKE_ACCESS, document_id):
            logger.error(f"User {revoked_by} not authorized to revoke access")
            return False
        
        if document_id not in self.acls:
            logger.error(f"Document {document_id} not found")
            return False
        
        acl = self.acls[document_id]
        all_permissions = list(DocumentPermission)
        acl.revoke_permission(document_id, user_id, all_permissions, revoked_by)
        
        logger.info(f"Access revoked for user {user_id} to document {document_id}")
        return True
    
    def get_user_documents(
        self,
        user_id: str,
        permission: DocumentPermission = DocumentPermission.VIEW_METADATA
    ) -> List[str]:
        """Get list of documents user can access"""
        documents = []
        
        for doc_id, acl in self.acls.items():
            if acl.has_permission(user_id, permission):
                documents.append(doc_id)
        
        return documents
    
    def get_access_report(self, document_id: str) -> Dict:
        """Get detailed access report for document"""
        if document_id not in self.acls:
            return {}
        
        acl = self.acls[document_id]
        return {
            'document_id': document_id,
            'owner': acl.owner,
            'created_at': acl.created_at.isoformat(),
            'last_modified': acl.last_modified.isoformat(),
            'access_entries': len(acl.permissions),
            'detailed_access': acl.get_all_access()
        }


# Global access controller instance
_access_controller = None

def get_access_controller() -> DocumentAccessController:
    """Get or create global access controller instance"""
    global _access_controller
    
    if _access_controller is None:
        _access_controller = DocumentAccessController()
    
    return _access_controller
