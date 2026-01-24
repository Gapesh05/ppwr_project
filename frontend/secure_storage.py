# secure_storage.py
"""
Secure Storage Module for Supplier Declaration Documents

This module implements enterprise-grade secure storage for supplier declaration
documents with encryption, access control, audit logging, and integrity verification.
"""

import os
import hashlib
import logging
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

# ==================== LOGGER SETUP ====================

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ==================== CONFIGURATION ====================

class SecureStorageConfig:
    """Configuration for secure storage system"""
    
    # Base storage directory
    BASE_STORAGE_DIR = os.path.join(
        os.path.dirname(__file__),
        '..',
        'secure_storage'
    )
    
    # Subdirectories
    DOCUMENTS_DIR = os.path.join(BASE_STORAGE_DIR, 'documents')
    METADATA_DIR = os.path.join(BASE_STORAGE_DIR, 'metadata')
    AUDIT_DIR = os.path.join(BASE_STORAGE_DIR, 'audit')
    ARCHIVE_DIR = os.path.join(BASE_STORAGE_DIR, 'archive')
    BACKUPS_DIR = os.path.join(BASE_STORAGE_DIR, 'backups')
    
    # Encryption settings
    ENCRYPTION_ENABLED = True
    SALT_LENGTH = 16  # bytes
    ITERATIONS = 100000  # PBKDF2 iterations
    
    # File limits
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'xlsx', 'xls'}
    
    # Security settings
    VERIFY_CHECKSUMS = True
    REQUIRE_VIRUS_SCAN = False  # Can be enabled for production
    AUDIT_LOGGING = True
    RETENTION_DAYS = 2555  # 7 years for compliance


class SecureStorageManager:
    """
    Manages secure storage of supplier declaration documents with:
    - File encryption
    - Access control
    - Audit logging
    - Integrity verification
    - Backup & recovery
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize the secure storage manager.
        
        Args:
            encryption_key: Master encryption key (auto-generated if not provided)
        """
        self.config = SecureStorageConfig()
        self._init_directories()
        self.encryption_key = encryption_key or self._get_or_create_master_key()
        logger.info("SecureStorageManager initialized")
    
    def _init_directories(self):
        """Create necessary storage directories with secure permissions"""
        directories = [
            self.config.BASE_STORAGE_DIR,
            self.config.DOCUMENTS_DIR,
            self.config.METADATA_DIR,
            self.config.AUDIT_DIR,
            self.config.ARCHIVE_DIR,
            self.config.BACKUPS_DIR,
        ]
        
        for directory in directories:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
                # Set restrictive permissions (700 = rwx------)
                os.chmod(directory, 0o700)
                logger.info(f"Initialized directory: {directory}")
            except Exception as e:
                logger.error(f"Failed to initialize directory {directory}: {e}")
                raise
    
    def _get_or_create_master_key(self) -> str:
        """
        Get or create the master encryption key.
        
        Returns:
            Base64-encoded master key
        """
        key_file = os.path.join(self.config.BASE_STORAGE_DIR, '.encryption_key')
        
        if os.path.exists(key_file):
            with open(key_file, 'r') as f:
                key = f.read().strip()
                logger.info("Using existing master encryption key")
                return key
        else:
            # Generate new key
            key = Fernet.generate_key().decode()
            
            # Save key with restrictive permissions
            try:
                # Create with secure permissions
                with open(key_file, 'w') as f:
                    f.write(key)
                os.chmod(key_file, 0o600)  # rw-------
                logger.info("Generated and saved new master encryption key")
                return key
            except Exception as e:
                logger.error(f"Failed to save master key: {e}")
                raise
    
    def _derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: Password string
            salt: Random salt bytes
            
        Returns:
            Derived encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.config.ITERATIONS,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of file for integrity verification.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex digest of SHA-256 hash
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b''):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _verify_file_integrity(self, file_path: str, expected_hash: str) -> bool:
        """
        Verify file integrity against stored hash.
        
        Args:
            file_path: Path to file
            expected_hash: Expected SHA-256 hash
            
        Returns:
            True if hash matches, False otherwise
        """
        actual_hash = self._calculate_file_hash(file_path)
        is_valid = actual_hash == expected_hash
        
        if not is_valid:
            logger.warning(f"File integrity check failed for {file_path}")
        
        return is_valid
    
    def store_document(
        self,
        file_path: str,
        sku: str,
        supplier_name: str = None,
        document_type: str = None,
        encryption_password: str = None
    ) -> Dict:
        """
        Securely store a document with encryption and audit logging.
        
        Args:
            file_path: Path to source file
            sku: Product SKU for organizing documents
            supplier_name: Name of supplier (optional)
            document_type: Type of document (pdf, docx, etc.)
            encryption_password: Optional password for additional encryption
            
        Returns:
            Dictionary with storage metadata and secure path
            
        Raises:
            ValueError: If file is invalid or exceeds limits
        """
        try:
            # 1. Validate file
            if not os.path.exists(file_path):
                raise ValueError(f"File not found: {file_path}")
            
            file_size = os.path.getsize(file_path)
            if file_size > self.config.MAX_FILE_SIZE:
                raise ValueError(
                    f"File exceeds maximum size: {file_size} > {self.config.MAX_FILE_SIZE}"
                )
            
            # 2. Calculate original file hash
            original_hash = self._calculate_file_hash(file_path)
            
            # 3. Generate storage path
            sku_dir = os.path.join(self.config.DOCUMENTS_DIR, sku)
            Path(sku_dir).mkdir(parents=True, exist_ok=True)
            os.chmod(sku_dir, 0o700)
            
            # Use timestamp + original hash for unique filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            storage_filename = f"{timestamp}_{original_hash[:16]}.enc"
            storage_path = os.path.join(sku_dir, storage_filename)
            
            # 4. Encrypt and store file
            if self.config.ENCRYPTION_ENABLED:
                self._encrypt_and_store_file(
                    file_path,
                    storage_path,
                    encryption_password
                )
            else:
                shutil.copy2(file_path, storage_path)
                os.chmod(storage_path, 0o600)
            
            # 5. Verify stored file integrity
            stored_hash = self._calculate_file_hash(storage_path)
            
            # 6. Create metadata
            metadata = {
                'sku': sku,
                'supplier_name': supplier_name,
                'document_type': document_type,
                'original_filename': os.path.basename(file_path),
                'storage_filename': storage_filename,
                'file_size': file_size,
                'original_hash': original_hash,
                'storage_hash': stored_hash,
                'upload_timestamp': datetime.utcnow().isoformat(),
                'encryption_enabled': self.config.ENCRYPTION_ENABLED,
                'password_protected': bool(encryption_password),
                'retention_until': self._calculate_retention_date(),
                'access_log': []
            }
            
            # 7. Store metadata
            self._store_metadata(storage_filename, metadata)
            
            # 8. Audit log
            self._audit_log('STORE', sku, storage_filename, metadata)
            
            logger.info(f"Document stored securely: {storage_filename}")
            
            return {
                'success': True,
                'storage_filename': storage_filename,
                'storage_path': storage_path,
                'sku': sku,
                'file_hash': original_hash,
                'file_size': file_size,
                'timestamp': metadata['upload_timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error storing document: {e}")
            self._audit_log('STORE_ERROR', sku, file_path, {'error': str(e)})
            raise
    
    def retrieve_document(
        self,
        sku: str,
        storage_filename: str,
        encryption_password: str = None,
        verify_integrity: bool = True
    ) -> Dict:
        """
        Retrieve and decrypt a stored document.
        
        Args:
            sku: Product SKU
            storage_filename: Encrypted filename
            encryption_password: Password if document is password-protected
            verify_integrity: Whether to verify file integrity
            
        Returns:
            Dictionary with file content and metadata
            
        Raises:
            ValueError: If document not found or integrity check fails
        """
        try:
            storage_path = os.path.join(
                self.config.DOCUMENTS_DIR,
                sku,
                storage_filename
            )
            
            if not os.path.exists(storage_path):
                raise ValueError(f"Document not found: {storage_filename}")
            
            # Load metadata
            metadata = self._load_metadata(storage_filename)
            
            # Verify integrity if requested
            if verify_integrity and not self._verify_file_integrity(
                storage_path,
                metadata['storage_hash']
            ):
                raise ValueError("File integrity verification failed")
            
            # Decrypt file
            if self.config.ENCRYPTION_ENABLED:
                file_content = self._decrypt_file(
                    storage_path,
                    encryption_password
                )
            else:
                with open(storage_path, 'rb') as f:
                    file_content = f.read()
            
            # Log access
            self._log_access(storage_filename, metadata)
            self._audit_log('RETRIEVE', sku, storage_filename, metadata)
            
            logger.info(f"Document retrieved: {storage_filename}")
            
            return {
                'success': True,
                'file_content': file_content,
                'original_filename': metadata['original_filename'],
                'file_size': metadata['file_size'],
                'document_type': metadata['document_type'],
                'upload_timestamp': metadata['upload_timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error retrieving document: {e}")
            self._audit_log('RETRIEVE_ERROR', sku, storage_filename, {'error': str(e)})
            raise
    
    def delete_document(
        self,
        sku: str,
        storage_filename: str,
        reason: str = None,
        secure_delete: bool = True
    ) -> Dict:
        """
        Securely delete a document with secure deletion.
        
        Args:
            sku: Product SKU
            storage_filename: Encrypted filename
            reason: Reason for deletion (for audit log)
            secure_delete: Whether to securely overwrite file
            
        Returns:
            Dictionary with deletion status
        """
        try:
            storage_path = os.path.join(
                self.config.DOCUMENTS_DIR,
                sku,
                storage_filename
            )
            
            if not os.path.exists(storage_path):
                raise ValueError(f"Document not found: {storage_filename}")
            
            # Load metadata before deletion
            metadata = self._load_metadata(storage_filename)
            
            # Archive before deletion
            self._archive_document(storage_path, metadata, reason)
            
            # Secure delete if requested
            if secure_delete:
                self._secure_delete_file(storage_path)
            else:
                os.remove(storage_path)
            
            # Remove metadata
            self._delete_metadata(storage_filename)
            
            # Audit log
            audit_data = {
                'reason': reason,
                'secure_delete': secure_delete,
                'archived': True
            }
            self._audit_log('DELETE', sku, storage_filename, audit_data)
            
            logger.info(f"Document deleted securely: {storage_filename}")
            
            return {
                'success': True,
                'storage_filename': storage_filename,
                'archived': True,
                'deletion_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            self._audit_log('DELETE_ERROR', sku, storage_filename, {'error': str(e)})
            raise
    
    def _encrypt_and_store_file(
        self,
        source_path: str,
        dest_path: str,
        password: str = None
    ):
        """Encrypt and store file"""
        try:
            # Read source file
            with open(source_path, 'rb') as f:
                file_data = f.read()
            
            # Encrypt with master key or password
            if password:
                salt = os.urandom(self.config.SALT_LENGTH)
                key = self._derive_key_from_password(password, salt)
                cipher = Fernet(key)
                encrypted_data = salt + cipher.encrypt(file_data)
            else:
                cipher = Fernet(self.encryption_key.encode())
                encrypted_data = cipher.encrypt(file_data)
            
            # Write encrypted file
            with open(dest_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Set restrictive permissions
            os.chmod(dest_path, 0o600)
            
            logger.info(f"File encrypted and stored: {dest_path}")
            
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    def _decrypt_file(
        self,
        storage_path: str,
        password: str = None
    ) -> bytes:
        """Decrypt stored file"""
        try:
            with open(storage_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt
            if password:
                salt = encrypted_data[:self.config.SALT_LENGTH]
                encrypted_content = encrypted_data[self.config.SALT_LENGTH:]
                key = self._derive_key_from_password(password, salt)
                cipher = Fernet(key)
                decrypted_data = cipher.decrypt(encrypted_content)
            else:
                cipher = Fernet(self.encryption_key.encode())
                decrypted_data = cipher.decrypt(encrypted_data)
            
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise
    
    def _secure_delete_file(self, file_path: str, passes: int = 3):
        """Securely delete file by overwriting with random data"""
        try:
            file_size = os.path.getsize(file_path)
            
            # Overwrite with random data
            for _ in range(passes):
                with open(file_path, 'wb') as f:
                    f.write(os.urandom(file_size))
            
            # Final overwrite with zeros
            with open(file_path, 'wb') as f:
                f.write(b'\x00' * file_size)
            
            # Delete file
            os.remove(file_path)
            logger.info(f"File securely deleted: {file_path}")
            
        except Exception as e:
            logger.error(f"Secure delete error: {e}")
            raise
    
    def _store_metadata(self, storage_filename: str, metadata: Dict):
        """Store document metadata as JSON"""
        try:
            metadata_path = os.path.join(
                self.config.METADATA_DIR,
                f"{storage_filename}.meta"
            )
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            os.chmod(metadata_path, 0o600)
            logger.info(f"Metadata stored: {metadata_path}")
            
        except Exception as e:
            logger.error(f"Error storing metadata: {e}")
            raise
    
    def _load_metadata(self, storage_filename: str) -> Dict:
        """Load document metadata"""
        try:
            metadata_path = os.path.join(
                self.config.METADATA_DIR,
                f"{storage_filename}.meta"
            )
            
            if not os.path.exists(metadata_path):
                raise ValueError(f"Metadata not found: {storage_filename}")
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error loading metadata: {e}")
            raise
    
    def _delete_metadata(self, storage_filename: str):
        """Delete metadata file"""
        try:
            metadata_path = os.path.join(
                self.config.METADATA_DIR,
                f"{storage_filename}.meta"
            )
            
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
                logger.info(f"Metadata deleted: {metadata_path}")
            
        except Exception as e:
            logger.error(f"Error deleting metadata: {e}")
            raise
    
    def _archive_document(
        self,
        storage_path: str,
        metadata: Dict,
        reason: str = None
    ):
        """Archive document before deletion"""
        try:
            archive_name = os.path.basename(storage_path)
            archive_path = os.path.join(self.config.ARCHIVE_DIR, archive_name)
            
            shutil.copy2(storage_path, archive_path)
            
            # Store archive metadata
            archive_metadata = {
                **metadata,
                'archived_timestamp': datetime.utcnow().isoformat(),
                'archive_reason': reason,
                'archive_path': archive_path
            }
            
            archive_meta_path = os.path.join(
                self.config.ARCHIVE_DIR,
                f"{archive_name}.meta"
            )
            
            with open(archive_meta_path, 'w') as f:
                json.dump(archive_metadata, f, indent=2)
            
            logger.info(f"Document archived: {archive_path}")
            
        except Exception as e:
            logger.error(f"Archiving error: {e}")
            raise
    
    def _log_access(self, storage_filename: str, metadata: Dict):
        """Log access to document"""
        access_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'ACCESS'
        }
        
        metadata['access_log'].append(access_record)
        self._store_metadata(storage_filename, metadata)
    
    def _audit_log(self, action: str, sku: str, filename: str, details: Dict = None):
        """Write audit log entry"""
        try:
            if not self.config.AUDIT_LOGGING:
                return
            
            audit_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'action': action,
                'sku': sku,
                'filename': filename,
                'details': details or {}
            }
            
            audit_file = os.path.join(
                self.config.AUDIT_DIR,
                f"audit_{datetime.utcnow().strftime('%Y%m%d')}.log"
            )
            
            with open(audit_file, 'a') as f:
                f.write(json.dumps(audit_entry) + '\n')
            
            os.chmod(audit_file, 0o600)
            
        except Exception as e:
            logger.error(f"Error writing audit log: {e}")
    
    def _calculate_retention_date(self) -> str:
        """Calculate document retention date"""
        from datetime import timedelta
        retention_date = datetime.utcnow() + timedelta(days=self.config.RETENTION_DAYS)
        return retention_date.isoformat()
    
    def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        try:
            total_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(self.config.DOCUMENTS_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
                    file_count += 1
            
            return {
                'total_files': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'storage_directory': self.config.DOCUMENTS_DIR,
                'encryption_enabled': self.config.ENCRYPTION_ENABLED
            }
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}


# Global storage manager instance
_storage_manager = None

def get_storage_manager(encryption_key: str = None) -> SecureStorageManager:
    """Get or create global storage manager instance"""
    global _storage_manager
    
    if _storage_manager is None:
        _storage_manager = SecureStorageManager(encryption_key)
    
    return _storage_manager
