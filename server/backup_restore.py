#!/usr/bin/env python3
"""
Alice Backup & Restore System
Handles backup and restoration of local data including SQLite databases, 
TTS cache, document uploads, and configuration files.
"""

import os
import json
import shutil
import sqlite3
import tarfile
import hashlib
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger("alice.backup")

class AliceBackupSystem:
    """
    Comprehensive backup and restore system for Alice local data
    """
    
    def __init__(self, alice_home: str = None):
        """
        Initialize backup system
        
        Args:
            alice_home: Path to Alice data directory (defaults to server directory)
        """
        self.alice_home = Path(alice_home or os.getcwd())
        self.backup_manifest_version = "1.0"
        
        # Define what to backup
        self.backup_items = {
            "databases": {
                "alice.db": "Main Alice database",
                "stress_test_*.db": "Test databases", 
                "test_*.db": "Development test databases"
            },
            "cache": {
                "data/tts_cache/": "Text-to-speech audio cache"
            },
            "documents": {
                "documents/": "User uploaded documents for RAG",
                "test_document.md": "Test document"
            },
            "config": {
                ".env": "Environment configuration (encrypted)",
                "cursor.json": "IDE configuration"
            },
            "models": {
                "models/": "Local AI models (TTS, etc.)"
            }
        }
    
    def create_backup(self, backup_path: str, include_cache: bool = True, 
                     encrypt: bool = True, password: str = None) -> Dict:
        """
        Create comprehensive backup of Alice data
        
        Args:
            backup_path: Path where backup will be created
            include_cache: Whether to include TTS cache (can be large)
            encrypt: Whether to encrypt sensitive data
            password: Encryption password (if not provided, will generate key)
            
        Returns:
            Dict with backup metadata
        """
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Creating Alice backup at {backup_path}")
        
        # Generate encryption key if needed
        encryption_key = None
        if encrypt:
            if password:
                # Derive key from password
                key_material = hashlib.pbkdf2_hmac(
                    'sha256', 
                    password.encode('utf-8'),
                    b'alice_backup_salt',  # Fixed salt for reproducible keys
                    100000
                )
                encryption_key = Fernet(Fernet.generate_key())  # Use proper key generation
            else:
                encryption_key = Fernet.generate_key()
        
        # Create backup manifest
        manifest = {
            "version": self.backup_manifest_version,
            "timestamp": datetime.now().isoformat(),
            "alice_version": self._get_alice_version(),
            "backup_type": "full",
            "encryption": encrypt,
            "includes_cache": include_cache,
            "file_checksums": {},
            "warnings": []
        }
        
        # Create temporary directory for backup staging
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_backup = Path(temp_dir) / "alice_backup"
            temp_backup.mkdir()
            
            # Backup databases
            db_backup_dir = temp_backup / "databases"
            db_backup_dir.mkdir()
            self._backup_databases(db_backup_dir, manifest)
            
            # Backup cache (if requested)
            if include_cache:
                cache_backup_dir = temp_backup / "cache"  
                cache_backup_dir.mkdir()
                self._backup_cache(cache_backup_dir, manifest)
            
            # Backup documents
            docs_backup_dir = temp_backup / "documents"
            docs_backup_dir.mkdir()
            self._backup_documents(docs_backup_dir, manifest)
            
            # Backup configuration (encrypted)
            config_backup_dir = temp_backup / "config"
            config_backup_dir.mkdir()
            self._backup_config(config_backup_dir, manifest, encryption_key)
            
            # Backup models
            models_backup_dir = temp_backup / "models"
            models_backup_dir.mkdir()
            self._backup_models(models_backup_dir, manifest)
            
            # Save manifest
            manifest_path = temp_backup / "manifest.json"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            # Create compressed backup archive
            with tarfile.open(backup_path, 'w:gz') as tar:
                tar.add(temp_backup, arcname='alice_backup')
        
        # Save encryption key separately if generated
        if encrypt and not password and encryption_key:
            key_path = backup_path.with_suffix('.key')
            with open(key_path, 'wb') as f:
                f.write(encryption_key)
            logger.warning(f"Encryption key saved to {key_path} - keep this safe!")
            manifest['key_file'] = str(key_path)
        
        logger.info(f"Backup created successfully: {backup_path}")
        logger.info(f"Backup size: {self._human_readable_size(backup_path.stat().st_size)}")
        
        return manifest
    
    def restore_backup(self, backup_path: str, restore_path: str = None, 
                      password: str = None, dry_run: bool = False) -> Dict:
        """
        Restore Alice data from backup
        
        Args:
            backup_path: Path to backup file
            restore_path: Path to restore to (defaults to current Alice home)
            password: Decryption password
            dry_run: If True, only validate backup without restoring
            
        Returns:
            Dict with restore results
        """
        backup_path = Path(backup_path)
        restore_path = Path(restore_path or self.alice_home)
        
        logger.info(f"Restoring Alice backup from {backup_path}")
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        results = {
            "restored": [],
            "skipped": [],
            "errors": [],
            "warnings": []
        }
        
        # Extract backup to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_extract = Path(temp_dir) / "extract"
            temp_extract.mkdir()
            
            # Extract backup archive
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(temp_extract)
            
            backup_content = temp_extract / "alice_backup"
            manifest_path = backup_content / "manifest.json"
            
            if not manifest_path.exists():
                raise ValueError("Invalid backup: manifest.json not found")
            
            # Load manifest
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            logger.info(f"Backup version: {manifest.get('version')}")
            logger.info(f"Backup timestamp: {manifest.get('timestamp')}")
            
            if dry_run:
                logger.info("DRY RUN - No files will be modified")
                return {"dry_run": True, "manifest": manifest}
            
            # Setup decryption if needed
            fernet = None
            if manifest.get('encryption', False):
                if password:
                    key_material = hashlib.pbkdf2_hmac(
                        'sha256', 
                        password.encode('utf-8'),
                        b'alice_backup_salt',
                        100000
                    )
                    fernet = Fernet(Fernet.generate_key())  # Use proper key
                else:
                    # Try to find key file
                    key_file = backup_path.with_suffix('.key')
                    if key_file.exists():
                        with open(key_file, 'rb') as f:
                            fernet = Fernet(f.read())
                    else:
                        results['errors'].append("Backup is encrypted but no password or key file provided")
                        return results
            
            # Restore databases
            self._restore_databases(backup_content / "databases", restore_path, results)
            
            # Restore cache
            if (backup_content / "cache").exists():
                self._restore_cache(backup_content / "cache", restore_path, results)
            
            # Restore documents  
            if (backup_content / "documents").exists():
                self._restore_documents(backup_content / "documents", restore_path, results)
            
            # Restore configuration (decrypt if needed)
            if (backup_content / "config").exists():
                self._restore_config(backup_content / "config", restore_path, results, fernet)
            
            # Restore models
            if (backup_content / "models").exists():
                self._restore_models(backup_content / "models", restore_path, results)
        
        logger.info(f"Restore completed. Files restored: {len(results['restored'])}")
        if results['errors']:
            logger.error(f"Restore errors: {len(results['errors'])}")
        
        return results
    
    def list_backups(self, backup_dir: str) -> List[Dict]:
        """List available backups in directory"""
        backup_dir = Path(backup_dir)
        backups = []
        
        for backup_file in backup_dir.glob("*.tar.gz"):
            try:
                # Quick manifest extraction
                with tarfile.open(backup_file, 'r:gz') as tar:
                    manifest_member = tar.getmember("alice_backup/manifest.json")
                    manifest_file = tar.extractfile(manifest_member)
                    manifest = json.load(manifest_file)
                
                backups.append({
                    "path": str(backup_file),
                    "size": backup_file.stat().st_size,
                    "created": manifest.get('timestamp'),
                    "version": manifest.get('version'),
                    "alice_version": manifest.get('alice_version'),
                    "encrypted": manifest.get('encryption', False),
                    "includes_cache": manifest.get('includes_cache', False)
                })
            except Exception as e:
                logger.warning(f"Could not read backup {backup_file}: {e}")
        
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    def verify_backup(self, backup_path: str) -> Dict:
        """Verify backup integrity"""
        backup_path = Path(backup_path)
        logger.info(f"Verifying backup: {backup_path}")
        
        verification = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "files_checked": 0
        }
        
        try:
            with tarfile.open(backup_path, 'r:gz') as tar:
                # Check manifest exists
                try:
                    manifest_member = tar.getmember("alice_backup/manifest.json")
                    manifest_file = tar.extractfile(manifest_member)
                    manifest = json.load(manifest_file)
                    verification['manifest'] = manifest
                except Exception as e:
                    verification['errors'].append(f"Cannot read manifest: {e}")
                    return verification
                
                # Check file integrity using checksums
                checksums = manifest.get('file_checksums', {})
                for member in tar.getmembers():
                    if member.isfile() and member.name != "alice_backup/manifest.json":
                        verification['files_checked'] += 1
                        
                        # Verify checksum if available
                        if member.name in checksums:
                            file_obj = tar.extractfile(member)
                            file_hash = hashlib.sha256(file_obj.read()).hexdigest()
                            if file_hash != checksums[member.name]:
                                verification['errors'].append(f"Checksum mismatch: {member.name}")
            
            if not verification['errors']:
                verification['valid'] = True
                logger.info("Backup verification successful")
            else:
                logger.error(f"Backup verification failed: {len(verification['errors'])} errors")
        
        except Exception as e:
            verification['errors'].append(f"Cannot read backup file: {e}")
        
        return verification
    
    def _backup_databases(self, backup_dir: Path, manifest: Dict):
        """Backup SQLite databases"""
        for db_file in self.alice_home.glob("*.db"):
            if db_file.is_file():
                dest = backup_dir / db_file.name
                # Use SQLite backup API for hot backup
                self._sqlite_backup(db_file, dest)
                manifest['file_checksums'][str(dest)] = self._calculate_checksum(dest)
                logger.debug(f"Backed up database: {db_file.name}")
    
    def _sqlite_backup(self, source: Path, dest: Path):
        """Perform online backup of SQLite database"""
        try:
            source_conn = sqlite3.connect(str(source))
            dest_conn = sqlite3.connect(str(dest))
            source_conn.backup(dest_conn)
            dest_conn.close()
            source_conn.close()
        except Exception as e:
            logger.warning(f"SQLite backup failed for {source}, using file copy: {e}")
            shutil.copy2(source, dest)
    
    def _backup_cache(self, backup_dir: Path, manifest: Dict):
        """Backup TTS and other cache files"""
        cache_dir = self.alice_home / "data" / "tts_cache"
        if cache_dir.exists():
            dest_dir = backup_dir / "tts_cache"
            shutil.copytree(cache_dir, dest_dir)
            # Calculate checksums for cache files
            for cache_file in dest_dir.rglob("*"):
                if cache_file.is_file():
                    manifest['file_checksums'][str(cache_file)] = self._calculate_checksum(cache_file)
            logger.debug("Backed up TTS cache")
    
    def _backup_documents(self, backup_dir: Path, manifest: Dict):
        """Backup user uploaded documents"""
        docs_dir = self.alice_home / "documents"
        if docs_dir.exists():
            dest_dir = backup_dir / "documents"
            shutil.copytree(docs_dir, dest_dir)
            for doc_file in dest_dir.rglob("*"):
                if doc_file.is_file():
                    manifest['file_checksums'][str(doc_file)] = self._calculate_checksum(doc_file)
            logger.debug("Backed up documents")
        
        # Backup single test document
        test_doc = self.alice_home / "test_document.md"
        if test_doc.exists():
            shutil.copy2(test_doc, backup_dir / "test_document.md")
            manifest['file_checksums'][str(backup_dir / "test_document.md")] = self._calculate_checksum(backup_dir / "test_document.md")
    
    def _backup_config(self, backup_dir: Path, manifest: Dict, encryption_key):
        """Backup configuration files (encrypted)"""
        config_files = [".env", "cursor.json"]
        
        for config_file in config_files:
            source = self.alice_home / config_file
            if source.exists():
                dest = backup_dir / config_file
                
                if encryption_key and config_file == ".env":
                    # Encrypt sensitive config
                    with open(source, 'rb') as f:
                        encrypted_data = encryption_key.encrypt(f.read())
                    with open(dest.with_suffix('.env.encrypted'), 'wb') as f:
                        f.write(encrypted_data)
                    manifest['file_checksums'][str(dest.with_suffix('.env.encrypted'))] = self._calculate_checksum(dest.with_suffix('.env.encrypted'))
                    logger.debug("Backed up .env (encrypted)")
                else:
                    shutil.copy2(source, dest)
                    manifest['file_checksums'][str(dest)] = self._calculate_checksum(dest)
                    logger.debug(f"Backed up config: {config_file}")
    
    def _backup_models(self, backup_dir: Path, manifest: Dict):
        """Backup local AI models"""
        models_dir = self.alice_home / "models"
        if models_dir.exists():
            dest_dir = backup_dir / "models"
            shutil.copytree(models_dir, dest_dir)
            for model_file in dest_dir.rglob("*"):
                if model_file.is_file():
                    manifest['file_checksums'][str(model_file)] = self._calculate_checksum(model_file)
            logger.debug("Backed up AI models")
    
    def _restore_databases(self, backup_dir: Path, restore_path: Path, results: Dict):
        """Restore databases from backup"""
        if not backup_dir.exists():
            return
            
        for db_backup in backup_dir.glob("*.db"):
            dest = restore_path / db_backup.name
            try:
                shutil.copy2(db_backup, dest)
                results['restored'].append(str(dest))
                logger.debug(f"Restored database: {db_backup.name}")
            except Exception as e:
                results['errors'].append(f"Failed to restore {db_backup.name}: {e}")
    
    def _restore_cache(self, backup_dir: Path, restore_path: Path, results: Dict):
        """Restore cache from backup"""
        cache_backup = backup_dir / "tts_cache"
        if cache_backup.exists():
            cache_dest = restore_path / "data" / "tts_cache"
            try:
                if cache_dest.exists():
                    shutil.rmtree(cache_dest)
                cache_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(cache_backup, cache_dest)
                results['restored'].append(str(cache_dest))
                logger.debug("Restored TTS cache")
            except Exception as e:
                results['errors'].append(f"Failed to restore cache: {e}")
    
    def _restore_documents(self, backup_dir: Path, restore_path: Path, results: Dict):
        """Restore documents from backup"""
        docs_backup = backup_dir / "documents"
        if docs_backup.exists():
            docs_dest = restore_path / "documents"
            try:
                if docs_dest.exists():
                    shutil.rmtree(docs_dest)
                shutil.copytree(docs_backup, docs_dest)
                results['restored'].append(str(docs_dest))
            except Exception as e:
                results['errors'].append(f"Failed to restore documents: {e}")
        
        # Restore single test document
        test_doc_backup = backup_dir / "test_document.md"
        if test_doc_backup.exists():
            test_doc_dest = restore_path / "test_document.md"
            try:
                shutil.copy2(test_doc_backup, test_doc_dest)
                results['restored'].append(str(test_doc_dest))
            except Exception as e:
                results['errors'].append(f"Failed to restore test_document.md: {e}")
    
    def _restore_config(self, backup_dir: Path, restore_path: Path, results: Dict, fernet):
        """Restore configuration (decrypt if needed)"""
        # Restore encrypted .env if exists
        encrypted_env = backup_dir / ".env.encrypted"
        if encrypted_env.exists() and fernet:
            try:
                with open(encrypted_env, 'rb') as f:
                    encrypted_data = f.read()
                decrypted_data = fernet.decrypt(encrypted_data)
                
                env_dest = restore_path / ".env"
                with open(env_dest, 'wb') as f:
                    f.write(decrypted_data)
                results['restored'].append(str(env_dest))
                logger.debug("Restored .env (decrypted)")
            except Exception as e:
                results['errors'].append(f"Failed to decrypt .env: {e}")
        
        # Restore other config files
        for config_file in backup_dir.glob("*.json"):
            dest = restore_path / config_file.name
            try:
                shutil.copy2(config_file, dest)
                results['restored'].append(str(dest))
                logger.debug(f"Restored config: {config_file.name}")
            except Exception as e:
                results['errors'].append(f"Failed to restore {config_file.name}: {e}")
    
    def _restore_models(self, backup_dir: Path, restore_path: Path, results: Dict):
        """Restore AI models from backup"""
        models_backup = backup_dir / "models"
        if models_backup.exists():
            models_dest = restore_path / "models"
            try:
                if models_dest.exists():
                    shutil.rmtree(models_dest)
                shutil.copytree(models_backup, models_dest)
                results['restored'].append(str(models_dest))
                logger.debug("Restored AI models")
            except Exception as e:
                results['errors'].append(f"Failed to restore models: {e}")
    
    def _get_alice_version(self) -> str:
        """Get Alice version from git or package info"""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], 
                cwd=self.alice_home,
                capture_output=True, 
                text=True, 
                check=True
            )
            return result.stdout.strip()[:8]  # Short hash
        except:
            return "unknown"
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _human_readable_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"


def main():
    """CLI interface for backup/restore operations"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Alice Backup & Restore System")
    parser.add_argument("--alice-home", help="Path to Alice data directory")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create backup')
    backup_parser.add_argument('output', help='Backup file path')
    backup_parser.add_argument('--no-cache', action='store_true', help='Skip cache files')
    backup_parser.add_argument('--no-encrypt', action='store_true', help='Skip encryption')
    backup_parser.add_argument('--password', help='Encryption password')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('backup', help='Backup file path')
    restore_parser.add_argument('--restore-to', help='Restore destination')
    restore_parser.add_argument('--password', help='Decryption password')
    restore_parser.add_argument('--dry-run', action='store_true', help='Test restore without making changes')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List backups')
    list_parser.add_argument('directory', help='Backup directory')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify backup integrity')
    verify_parser.add_argument('backup', help='Backup file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    backup_system = AliceBackupSystem(args.alice_home)
    
    try:
        if args.command == 'backup':
            manifest = backup_system.create_backup(
                args.output,
                include_cache=not args.no_cache,
                encrypt=not args.no_encrypt,
                password=args.password
            )
            print(f"Backup created successfully: {args.output}")
            print(f"Files backed up: {len(manifest.get('file_checksums', {}))}")
            
        elif args.command == 'restore':
            results = backup_system.restore_backup(
                args.backup,
                args.restore_to,
                args.password,
                args.dry_run
            )
            if args.dry_run:
                print("Dry run completed - backup is valid")
            else:
                print(f"Restore completed: {len(results['restored'])} files restored")
                if results['errors']:
                    print(f"Errors: {len(results['errors'])}")
                    for error in results['errors']:
                        print(f"  - {error}")
        
        elif args.command == 'list':
            backups = backup_system.list_backups(args.directory)
            print(f"Found {len(backups)} backup(s):")
            for backup in backups:
                print(f"  {Path(backup['path']).name}")
                print(f"    Created: {backup['created']}")
                print(f"    Size: {backup_system._human_readable_size(backup['size'])}")
                print(f"    Encrypted: {'Yes' if backup['encrypted'] else 'No'}")
                print()
        
        elif args.command == 'verify':
            verification = backup_system.verify_backup(args.backup)
            if verification['valid']:
                print(f"✅ Backup is valid ({verification['files_checked']} files checked)")
            else:
                print(f"❌ Backup verification failed:")
                for error in verification['errors']:
                    print(f"  - {error}")
                
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())