"""Backup functionality for Quicken files."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


def create_backup(quicken_file: Path, backup_dir: Optional[Path] = None) -> Path:
    """
    Create a timestamped backup of a Quicken file.

    Args:
        quicken_file: Path to .quicken file to backup
        backup_dir: Optional directory for backups (defaults to ./backups)

    Returns:
        Path to the created backup file
    """
    if backup_dir is None:
        backup_dir = Path.cwd() / "backups"

    backup_dir.mkdir(exist_ok=True)

    # Create timestamped backup name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{quicken_file.stem}_backup_{timestamp}{quicken_file.suffix}"
    backup_path = backup_dir / backup_name

    # Copy the entire .quicken package
    if quicken_file.is_dir():
        shutil.copytree(quicken_file, backup_path)
    else:
        shutil.copy2(quicken_file, backup_path)

    return backup_path
