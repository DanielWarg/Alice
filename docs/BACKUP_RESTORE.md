# Alice Backup & Restore System

Alice includes a comprehensive backup and restore system to protect your local data, including conversation history, uploaded documents, TTS cache, and configuration files.

## Quick Start

### Create a Backup

```bash
# Simple backup
./alice_backup backup my_alice_backup.tar.gz

# Backup without cache (smaller size)
./alice_backup backup --no-cache my_alice_backup.tar.gz

# Backup with password encryption
./alice_backup backup --password mypassword my_alice_backup.tar.gz
```

### Restore from Backup

```bash
# Restore to current directory
./alice_backup restore my_alice_backup.tar.gz

# Test restore without making changes
./alice_backup restore --dry-run my_alice_backup.tar.gz

# Restore with password
./alice_backup restore --password mypassword my_alice_backup.tar.gz
```

### List Backups

```bash
./alice_backup list /path/to/backup/directory
```

### Verify Backup Integrity

```bash
./alice_backup verify my_alice_backup.tar.gz
```

## What Gets Backed Up

### Databases
- `alice.db` - Main Alice conversation and memory database
- `*.db` - All SQLite databases in the server directory

### Cache Files (Optional)
- `data/tts_cache/` - Text-to-speech audio cache files
- Can be skipped with `--no-cache` to reduce backup size

### Documents
- `test_documents/` - User uploaded documents for RAG
- `test_document.md` - Individual test documents

### Configuration (Encrypted)
- `.env` - Environment variables (automatically encrypted)
- `cursor.json` - IDE configuration

### AI Models
- `models/` - Local TTS and other AI models

## Security Features

### Encryption
- Sensitive files like `.env` are automatically encrypted
- Optional password-based encryption for entire backup
- AES-256 encryption with PBKDF2 key derivation

### Integrity Verification
- SHA256 checksums for all files
- Backup verification before restoration
- Tamper detection

### Privacy Protection
- No external data transmission
- Local-only backup storage
- User-controlled retention

## Advanced Usage

### Python API

```python
from backup_restore import AliceBackupSystem

# Initialize backup system
backup_system = AliceBackupSystem("/path/to/alice")

# Create encrypted backup
manifest = backup_system.create_backup(
    "backup.tar.gz",
    include_cache=False,  # Skip cache for smaller backup
    encrypt=True,
    password="secure_password"
)

# Restore backup
results = backup_system.restore_backup(
    "backup.tar.gz",
    password="secure_password"
)

# List available backups
backups = backup_system.list_backups("/backup/directory")

# Verify backup integrity
verification = backup_system.verify_backup("backup.tar.gz")
```

### Automated Backups

You can schedule automatic backups using cron:

```bash
# Add to crontab (crontab -e)
# Backup every day at 2 AM
0 2 * * * cd /path/to/alice/server && ./alice_backup backup --no-cache daily_backup_$(date +\%Y\%m\%d).tar.gz

# Backup every week with full cache
0 2 * * 0 cd /path/to/alice/server && ./alice_backup backup weekly_backup_$(date +\%Y\%m\%d).tar.gz
```

## Backup Storage Recommendations

### Local Backup Storage
- Store backups on a different drive than Alice
- Use external drives or network storage
- Keep multiple backup generations

### Cloud Backup (Optional)
Since backups are encrypted, you can safely store them in cloud storage:

```bash
# Example: Upload to cloud storage after backup
./alice_backup backup encrypted_backup.tar.gz --password your_password
# Upload encrypted_backup.tar.gz to your preferred cloud storage
```

## Troubleshooting

### Large Backup Size
If backups are too large:
- Use `--no-cache` to skip TTS cache
- Clean up old conversation data before backup
- Consider separate model backups

### Restore Issues
If restore fails:
- Verify backup integrity first: `./alice_backup verify backup.tar.gz`
- Try dry-run restore: `./alice_backup restore --dry-run backup.tar.gz`
- Check disk space and permissions

### Encryption Problems
If you forgot your password:
- Check for `.key` file next to backup (generated without password)
- No password recovery possible - encryption is secure

### Permissions
If backup/restore fails with permission errors:
```bash
# Fix file permissions
chmod -R 755 /path/to/alice/server
# Make backup script executable
chmod +x alice_backup
```

## Migration Scenarios

### Moving to New Machine
1. Create backup on old machine: `./alice_backup backup migration.tar.gz`
2. Install Alice on new machine
3. Copy backup file to new machine
4. Restore: `./alice_backup restore migration.tar.gz`

### Version Upgrade
1. Backup current version: `./alice_backup backup pre_upgrade.tar.gz`
2. Upgrade Alice
3. If issues occur, restore: `./alice_backup restore pre_upgrade.tar.gz`

### Development/Production Sync
1. Backup production: `./alice_backup backup prod_backup.tar.gz --password prod_pass`
2. Restore to development: `./alice_backup restore prod_backup.tar.gz --password prod_pass`

## Security Best Practices

1. **Always encrypt backups** containing sensitive data
2. **Store backup passwords securely** (password manager)
3. **Test restore procedures** regularly
4. **Keep backups offline** when possible
5. **Rotate backup passwords** periodically
6. **Verify backup integrity** before depending on them

## File Formats

### Backup Archive Structure
```
alice_backup.tar.gz
├── alice_backup/
│   ├── manifest.json          # Backup metadata
│   ├── databases/            # SQLite databases
│   │   ├── alice.db
│   │   └── *.db
│   ├── cache/               # TTS cache (optional)
│   │   └── tts_cache/
│   ├── documents/           # User documents
│   │   ├── test_documents/
│   │   └── test_document.md
│   ├── config/              # Configuration
│   │   ├── .env.encrypted   # Encrypted environment
│   │   └── cursor.json
│   └── models/              # AI models
│       └── models/
```

### Manifest Format
```json
{
  "version": "1.0",
  "timestamp": "2025-01-22T14:30:00.123Z",
  "alice_version": "a1b2c3d4",
  "backup_type": "full",
  "encryption": true,
  "includes_cache": false,
  "file_checksums": {
    "databases/alice.db": "sha256:abc123...",
    ...
  },
  "warnings": []
}
```

---

For more information, see the Alice documentation or run `./alice_backup --help` for command-line options.