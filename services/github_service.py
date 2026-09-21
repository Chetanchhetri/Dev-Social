import os
import shutil
import zipfile
import re
import logging
import uuid
import unicodedata
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import text
from git import Repo, GitCommandError

from models.project import Project, ProjectOperation, OperationState

# Conditionally import Unix-only resource module for cross-platform compatibility
try:
    import resource
    HAS_RESOURCE_MODULE = True
except ImportError:
    HAS_RESOURCE_MODULE = False

# Structured Security Logger
logger = logging.getLogger("devsocial.security")

# Dedicated Storage Namespaces
BASE_MEDIA_DIR = os.path.abspath(os.getenv("MEDIA_DIR", "uploads"))
PROJECTS_ROOT = Path(os.path.join(BASE_MEDIA_DIR, "projects")).resolve()
STAGING_ROOT = Path(os.path.join(BASE_MEDIA_DIR, "staging")).resolve()
BACKUPS_ROOT = Path(os.path.join(BASE_MEDIA_DIR, "backups")).resolve()

# Security Limits
MAX_ZIP_UPLOAD_BYTES = 100 * 1024 * 1024        # 100 MB max upload
MAX_UNCOMPRESSED_SIZE_BYTES = 250 * 1024 * 1024  # 250 MB max project size
MAX_GIT_REPOSITORY_BYTES = 250 * 1024 * 1024     # 250 MB max working tree
MAX_GIT_METADATA_BYTES = 50 * 1024 * 1024        # 50 MB max .git metadata
MAX_INDIVIDUAL_FILE_BYTES = 50 * 1024 * 1024     # 50 MB max single file
MAX_ARCHIVE_ENTRIES = 1000                       # Max 1,000 files/folders
MAX_COMPRESSION_RATIO = 10.0                     # Max 10:1 compression ratio
MAX_DIRECTORY_DEPTH = 25                         # Max 25 levels of nesting
MAX_PATH_LENGTH = 255                            # Max 255 chars for relative path
MAX_PROJECT_NAME_LENGTH = 100                    # Max 100 chars for title
PER_USER_STORAGE_QUOTA_BYTES = 1 * 1024 * 1024 * 1024  # 1 GB quota per user
MIN_REQUIRED_FREE_DISK_BYTES = 1 * 1024 * 1024 * 1024  # 1 GB free host disk required
GIT_OPERATION_TIMEOUT_SECONDS = 30              # 30-second timeout for Git operations


class GitHubService:

    @classmethod
    def initialize_storage_directories(cls):
        """Ensures isolated root storage directories exist at application startup."""
        for path in [PROJECTS_ROOT, STAGING_ROOT, BACKUPS_ROOT]:
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_project_name(name: str) -> str:
        """Validates project display name."""
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Project name cannot be empty.")
        if len(name.strip()) > MAX_PROJECT_NAME_LENGTH:
            raise HTTPException(status_code=400, detail=f"Project name exceeds limit of {MAX_PROJECT_NAME_LENGTH} chars.")
        return name.strip()

    @staticmethod
    def _parse_and_validate_github_url(url: str) -> str:
        """Strictly parses GitHub repository URLs to require exactly /owner/repo without query or fragments."""
        try:
            parsed = urllib.parse.urlparse(url.strip())
            if parsed.scheme != "https":
                raise HTTPException(status_code=400, detail="Only HTTPS GitHub URLs are allowed.")
            if parsed.hostname not in {"github.com", "www.github.com"}:
                raise HTTPException(status_code=400, detail="Repository host must be github.com.")
            if parsed.username or parsed.password:
                raise HTTPException(status_code=400, detail="Embedded credentials in URLs are strictly prohibited.")
            if parsed.query or parsed.fragment:
                raise HTTPException(status_code=400, detail="URL query parameters and fragments are not supported.")

            path_parts = [p for p in parsed.path.strip("/").split("/") if p]
            if len(path_parts) != 2:
                raise HTTPException(status_code=400, detail="GitHub URL must strictly match 'https://github.com/owner/repository'.")

            owner, repo_name = path_parts[0], path_parts[1]
            repo_name = repo_name[:-4] if repo_name.endswith(".git") else repo_name
            
            if not re.match(r"^[a-zA-Z0-9_.-]+$", owner) or not re.match(r"^[a-zA-Z0-9_.-]+$", repo_name):
                raise HTTPException(status_code=400, detail="Invalid characters in GitHub repository path.")

            return f"https://github.com/{owner}/{repo_name}.git"
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Malformed GitHub URL provided.")

    @classmethod
    def _acquire_project_advisory_lock(cls, db: Session, user_id: int, project_identifier: str):
        """Acquires a deterministic PostgreSQL 64-bit advisory lock using hashtext()."""
        try:
            lock_key = f"{user_id}:{project_identifier}"
            db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"), {"lock_key": lock_key})
        except Exception as e:
            logger.error(f"[LOCK_ERROR] Advisory lock acquisition failed for {user_id}:{project_identifier} - {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to acquire lock for project operation.")

    @classmethod
    def _check_host_disk_safety(cls, required_bytes: int):
        """Verifies host filesystem space. FAILS CLOSED if disk inspection fails."""
        try:
            _, _, free = shutil.disk_usage(str(BASE_MEDIA_DIR))
            if free < MIN_REQUIRED_FREE_DISK_BYTES or free < required_bytes:
                logger.critical(f"[DISK_SPACE_LOW] Free disk space ({free} bytes) below safe threshold.")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Server storage capacity unavailable. Try again later."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.critical(f"[DISK_INSPECTION_FAILED] Fail-closed: Could not inspect disk usage - {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage capacity inspection failed. Operation aborted for safety."
            )

    @classmethod
    def _calculate_user_disk_usage(cls, db: Session, user_id: int) -> int:
        """Calculates total disk usage for a user from indexed project files plus active reservations."""
        user_dir = PROJECTS_ROOT / f"user_{user_id}"
        disk_bytes = 0
        if user_dir.exists():
            for path in user_dir.rglob('*'):
                if path.is_file() and not path.is_symlink():
                    disk_bytes += path.stat().st_size

        active_ops = db.query(ProjectOperation).filter(
            ProjectOperation.user_id == user_id,
            ProjectOperation.state.in_([OperationState.CREATED, OperationState.RESERVED, OperationState.STAGED])
        ).all()
        reserved_bytes = sum(op.reserved_bytes for op in active_ops)

        return disk_bytes + reserved_bytes

    @classmethod
    def _create_operation_reservation_atomic(
        cls, 
        db: Session, 
        user_id: int, 
        project_uuid: str, 
        expected_bytes: int, 
        existing_project_uuid: Optional[str] = None
    ) -> ProjectOperation:
        """Durable quota reservation using db.flush() to retain the transaction lock."""
        try:
            db.execute(text("SELECT id FROM users WHERE id = :user_id FOR UPDATE"), {"user_id": user_id})

            current_usage = cls._calculate_user_disk_usage(db, user_id)
            existing_bytes = 0

            if existing_project_uuid:
                existing_dir = PROJECTS_ROOT / f"user_{user_id}" / existing_project_uuid
                if existing_dir.exists():
                    existing_bytes = sum(f.stat().st_size for f in existing_dir.rglob('*') if f.is_file() and not f.is_symlink())

            projected_usage = (current_usage - existing_bytes) + expected_bytes
            if projected_usage > PER_USER_STORAGE_QUOTA_BYTES:
                limit_mb = PER_USER_STORAGE_QUOTA_BYTES // (1024 * 1024)
                logger.warning(f"[QUOTA_EXCEEDED] User {user_id} projected usage ({projected_usage} bytes) exceeds {limit_mb} MB.")
                raise HTTPException(status_code=400, detail=f"Storage quota exceeded. Maximum allowed per user is {limit_mb} MB.")

            operation = ProjectOperation(
                user_id=user_id,
                project_uuid=project_uuid,
                state=OperationState.RESERVED,
                reserved_bytes=expected_bytes
            )
            db.add(operation)
            db.flush()
            return operation
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[QUOTA_RESERVATION_FAILED] Reservation failed for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Storage quota reservation failed.")

    @classmethod
    def _validate_directory_structure(cls, root_dir: Path, is_git: bool = False) -> int:
        """Audits directory contents, depths, per-file limits, root .git metadata, and symlinks."""
        file_count = 0
        working_tree_size = 0
        git_metadata_size = 0

        for path in root_dir.rglob('*'):
            try:
                rel_path = path.relative_to(root_dir)
            except ValueError:
                logger.error(f"[PATH_OUT_OF_BOUNDS] Directory traversal detected: {path}")
                raise HTTPException(status_code=400, detail="Invalid path structure inside project directory.")

            if len(str(rel_path)) > MAX_PATH_LENGTH:
                raise HTTPException(status_code=400, detail=f"Path length exceeds maximum limit of {MAX_PATH_LENGTH} chars.")

            if path.is_symlink():
                err_code = "GIT_REJECTED_SYMLINK" if is_git else "ZIP_REJECTED_SYMLINK"
                logger.warning(f"[{err_code}] Symbolic link detected and rejected: {path}")
                raise HTTPException(status_code=400, detail="Symbolic links are strictly prohibited inside projects.")

            if not path.is_file() and not path.is_dir():
                raise HTTPException(status_code=400, detail="Special filesystem entries (pipes/sockets/devices) detected and rejected.")

            if len(rel_path.parts) > MAX_DIRECTORY_DEPTH:
                raise HTTPException(status_code=400, detail=f"Directory nesting exceeds limit of {MAX_DIRECTORY_DEPTH} levels.")

            # Strict Root .git Detection Logic
            if is_git and len(rel_path.parts) > 0 and rel_path.parts[0] == ".git":
                if path.is_file():
                    git_metadata_size += path.stat().st_size
                    if git_metadata_size > MAX_GIT_METADATA_BYTES:
                        logger.warning(f"[GIT_METADATA_EXCEEDED] Root .git directory size exceeds {MAX_GIT_METADATA_BYTES} bytes.")
                        raise HTTPException(status_code=400, detail="Git repository metadata (.git) exceeds 50 MB limit.")
                continue

            file_count += 1
            if file_count > MAX_ARCHIVE_ENTRIES:
                raise HTTPException(status_code=400, detail=f"Project contains too many entries ({file_count}). Limit is {MAX_ARCHIVE_ENTRIES}.")

            if path.is_file():
                file_size = path.stat().st_size
                if file_size > MAX_INDIVIDUAL_FILE_BYTES:
                    raise HTTPException(status_code=400, detail=f"File '{path.name}' exceeds maximum limit of 50 MB.")
                working_tree_size += file_size

        max_limit = MAX_GIT_REPOSITORY_BYTES if is_git else MAX_UNCOMPRESSED_SIZE_BYTES
        if working_tree_size > max_limit:
            logger.warning(f"[SIZE_LIMIT_EXCEEDED] Working tree size ({working_tree_size} bytes) exceeds limit ({max_limit} bytes).")
            raise HTTPException(status_code=400, detail=f"Working tree exceeds size limit of {max_limit // (1024 * 1024)} MB.")

        return working_tree_size + git_metadata_size

    @classmethod
    def _execute_sandboxed_git_clone(cls, repo_url: str, target_dir: Path):
        """Executes Git clone inside an isolated process environment with system resource limits."""
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_HTTP_LOW_SPEED_LIMIT": "1000",
            "GIT_HTTP_LOW_SPEED_TIME": str(GIT_OPERATION_TIMEOUT_SECONDS),
            "GIT_ALLOW_PROTOCOL": "https",
            "GIT_TERMINAL_PROMPT": "0",
            "HOME": str(STAGING_ROOT)
        }

        # Apply resource limits on Linux/Unix systems if resource module exists
        preexec_fn = None
        if HAS_RESOURCE_MODULE:
            def process_resource_preexec():
                resource.setrlimit(resource.RLIMIT_CPU, (30, 35))
                resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
                resource.setrlimit(resource.RLIMIT_NPROC, (20, 20))
            preexec_fn = process_resource_preexec

        try:
            Repo.clone_from(
                repo_url, 
                target_dir, 
                depth=1, 
                env=env,
                multi_options=[
                    "--no-recurse-submodules", 
                    "--config core.hooksPath=/dev/null",
                    "--config core.filter=/dev/null",
                    "--config core.symlinks=false"
                ],
                preexec_fn=preexec_fn,
                kill_after_timeout=GIT_OPERATION_TIMEOUT_SECONDS
            )
        except GitCommandError as e:
            logger.error(f"[SANDBOX_GIT_CLONE_FAIL] Sandboxed clone failed: {str(e)}")
            raise HTTPException(status_code=400, detail="Failed to clone repository inside sandbox.")

    @classmethod
    def clone_repository(cls, db: Session, github_url: str, user_id: int, project_title: str) -> Dict[str, Any]:
        """State-machine driven GitHub repository import pipeline."""
        title = cls._validate_project_name(project_title)
        project_uuid = str(uuid.uuid4())

        cls._acquire_project_advisory_lock(db, user_id, title)
        cls._check_host_disk_safety((MAX_GIT_REPOSITORY_BYTES + MAX_GIT_METADATA_BYTES) * 2)

        repo_url = cls._parse_and_validate_github_url(github_url)
        operation = cls._create_operation_reservation_atomic(db, user_id, project_uuid, MAX_GIT_REPOSITORY_BYTES + MAX_GIT_METADATA_BYTES)

        staging_dir = STAGING_ROOT / operation.id
        target_dir = PROJECTS_ROOT / f"user_{user_id}" / project_uuid
        staging_dir.mkdir(parents=True, exist_ok=True)

        try:
            cls._execute_sandboxed_git_clone(repo_url, staging_dir)
            operation.state = OperationState.STAGED
            db.flush()

            actual_bytes = cls._validate_directory_structure(staging_dir, is_git=True)
            operation.actual_bytes = actual_bytes

            backup_dir = BACKUPS_ROOT / f"backup_{operation.id}"
            if target_dir.exists():
                shutil.move(str(target_dir), str(backup_dir))

            target_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staging_dir), str(target_dir))
            operation.state = OperationState.PROMOTED

            file_tree_result = cls.build_file_tree(str(target_dir))

            project = Project(
                uuid=project_uuid,
                user_id=user_id,
                title=title,
                source_type="GITHUB",
                github_url=repo_url,
                disk_directory=str(target_dir),
                disk_size_bytes=actual_bytes,
                file_tree=file_tree_result
            )
            db.add(project)
            operation.state = OperationState.COMPLETED
            db.commit()

            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)

            return {
                "project_id": project.id,
                "project_uuid": project.uuid,
                "title": project.title,
                "file_tree": file_tree_result
            }

        except Exception as e:
            db.rollback()
            operation.state = OperationState.FAILED
            db.commit()
            logger.error(f"[CLONE_OPERATION_FAILED] Operation {operation.id} failed: {str(e)}")
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)
            raise

    @classmethod
    def extract_zip_project(cls, db: Session, file: UploadFile, user_id: int, project_title: str) -> Dict[str, Any]:
        """State-machine driven ZIP extraction pipeline."""
        title = cls._validate_project_name(project_title)
        project_uuid = str(uuid.uuid4())

        cls._acquire_project_advisory_lock(db, user_id, title)
        cls._check_host_disk_safety(MAX_UNCOMPRESSED_SIZE_BYTES + MAX_ZIP_UPLOAD_BYTES)

        if not file.filename or not file.filename.lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail="Only .zip archives are supported.")

        operation = cls._create_operation_reservation_atomic(db, user_id, project_uuid, MAX_UNCOMPRESSED_SIZE_BYTES)

        staging_dir = STAGING_ROOT / operation.id
        target_dir = PROJECTS_ROOT / f"user_{user_id}" / project_uuid
        staging_dir.mkdir(parents=True, exist_ok=True)
        temp_zip_path = staging_dir / "uploaded.zip"

        try:
            uploaded_bytes = 0
            with open(temp_zip_path, "wb") as buffer:
                while chunk := file.file.read(1024 * 1024):
                    uploaded_bytes += len(chunk)
                    if uploaded_bytes > MAX_ZIP_UPLOAD_BYTES:
                        raise HTTPException(status_code=400, detail="Upload exceeds 100 MB limit.")
                    buffer.write(chunk)

            try:
                zip_ref = zipfile.ZipFile(temp_zip_path, "r")
            except (zipfile.BadZipFile, zipfile.LargeZipFile):
                raise HTTPException(status_code=400, detail="Uploaded file is a corrupted or malformed ZIP archive.")

            with zip_ref:
                file_list = zip_ref.infolist()

                if len(file_list) > MAX_ARCHIVE_ENTRIES:
                    raise HTTPException(status_code=400, detail=f"ZIP contains too many entries ({len(file_list)}). Limit is {MAX_ARCHIVE_ENTRIES}.")

                seen_filenames: Set[str] = set()
                declared_uncompressed_size = 0
                total_compressed_size = sum(m.compress_size for m in file_list) or 1

                for member in file_list:
                    if member.flag_bits & 0x1:
                        raise HTTPException(status_code=400, detail="Password-protected ZIP archives are not supported.")

                    normalized_member_path = unicodedata.normalize("NFC", member.filename.replace("\\", "/").strip("/"))
                    case_folded_name = normalized_member_path.casefold()

                    if case_folded_name in seen_filenames:
                        raise HTTPException(status_code=400, detail=f"Duplicate ZIP entry detected: '{member.filename}'.")
                    seen_filenames.add(case_folded_name)

                    if len(normalized_member_path) > MAX_PATH_LENGTH:
                        raise HTTPException(status_code=400, detail=f"ZIP path for '{member.filename}' exceeds limit of {MAX_PATH_LENGTH} chars.")

                    if member.file_size > MAX_INDIVIDUAL_FILE_BYTES:
                        raise HTTPException(status_code=400, detail=f"File '{member.filename}' header exceeds 50 MB limit.")

                    destination_path = (staging_dir / normalized_member_path).resolve()
                    try:
                        rel_path = destination_path.relative_to(staging_dir)
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Path traversal attempt detected inside ZIP archive.")

                    if len(rel_path.parts) > MAX_DIRECTORY_DEPTH:
                        raise HTTPException(status_code=400, detail=f"Directory nesting for '{member.filename}' exceeds {MAX_DIRECTORY_DEPTH} levels.")

                    declared_uncompressed_size += member.file_size

                if declared_uncompressed_size > MAX_UNCOMPRESSED_SIZE_BYTES:
                    raise HTTPException(status_code=400, detail="Declared uncompressed size exceeds 250 MB limit.")

                if (declared_uncompressed_size / total_compressed_size) > MAX_COMPRESSION_RATIO:
                    raise HTTPException(status_code=400, detail="Excessive compression ratio detected (Zip Bomb).")

                actual_extracted_bytes = 0
                for member in file_list:
                    if (member.external_attr >> 16) & 0o120000 == 0o120000:
                        raise HTTPException(status_code=400, detail="Symbolic links are prohibited inside archives.")

                    normalized_member_path = unicodedata.normalize("NFC", member.filename.replace("\\", "/").strip("/"))
                    destination_path = (staging_dir / normalized_member_path).resolve()

                    if member.is_dir():
                        destination_path.mkdir(parents=True, exist_ok=True)
                        continue

                    destination_path.parent.mkdir(parents=True, exist_ok=True)

                    with zip_ref.open(member) as source, open(destination_path, "wb") as target:
                        file_extracted_bytes = 0
                        while chunk := source.read(1024 * 64):
                            file_extracted_bytes += len(chunk)
                            actual_extracted_bytes += len(chunk)

                            if file_extracted_bytes > MAX_INDIVIDUAL_FILE_BYTES or actual_extracted_bytes > MAX_UNCOMPRESSED_SIZE_BYTES:
                                raise HTTPException(status_code=400, detail="Extraction aborted: Storage thresholds exceeded.")

                            target.write(chunk)

            os.remove(temp_zip_path)
            operation.state = OperationState.STAGED
            db.flush()

            actual_bytes = cls._validate_directory_structure(staging_dir, is_git=False)
            operation.actual_bytes = actual_bytes

            backup_dir = BACKUPS_ROOT / f"backup_{operation.id}"
            if target_dir.exists():
                shutil.move(str(target_dir), str(backup_dir))

            target_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staging_dir), str(target_dir))
            operation.state = OperationState.PROMOTED

            file_tree_result = cls.build_file_tree(str(target_dir))

            project = Project(
                uuid=project_uuid,
                user_id=user_id,
                title=title,
                source_type="ZIP",
                github_url=None,
                disk_directory=str(target_dir),
                disk_size_bytes=actual_bytes,
                file_tree=file_tree_result
            )
            db.add(project)
            operation.state = OperationState.COMPLETED
            db.commit()

            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)

            return {
                "project_id": project.id,
                "project_uuid": project.uuid,
                "title": project.title,
                "file_tree": file_tree_result
            }

        except Exception as e:
            db.rollback()
            operation.state = OperationState.FAILED
            db.commit()
            logger.error(f"[ZIP_OPERATION_FAILED] Operation {operation.id} failed: {str(e)}")
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)
            raise

    @classmethod
    def sync_pull_repo(cls, db: Session, project_id: int, user_id: int) -> Dict[str, Any]:
        """State-machine driven Git pull sync with pre-copy symlink validation."""
        project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized.")

        if project.source_type != "GITHUB":
            raise HTTPException(status_code=400, detail="Cannot sync ZIP-uploaded projects.")

        target_dir = Path(project.disk_directory).resolve()
        if not target_dir.exists():
            raise HTTPException(status_code=404, detail="Project storage directory missing.")

        # Pre-Audit Existing Working Tree for Symlinks Before Copying
        cls._validate_directory_structure(target_dir, is_git=True)

        cls._acquire_project_advisory_lock(db, user_id, project.title)
        cls._check_host_disk_safety((MAX_GIT_REPOSITORY_BYTES + MAX_GIT_METADATA_BYTES) * 2)

        operation = cls._create_operation_reservation_atomic(
            db, user_id, project.uuid, MAX_GIT_REPOSITORY_BYTES + MAX_GIT_METADATA_BYTES, existing_project_uuid=project.uuid
        )
        staging_dir = STAGING_ROOT / operation.id

        try:
            shutil.copytree(target_dir, staging_dir, symlinks=False)

            cls._execute_sandboxed_git_clone(project.github_url, staging_dir)
            operation.state = OperationState.STAGED
            db.flush()

            actual_bytes = cls._validate_directory_structure(staging_dir, is_git=True)
            operation.actual_bytes = actual_bytes

            backup_dir = BACKUPS_ROOT / f"backup_{operation.id}"
            if target_dir.exists():
                shutil.move(str(target_dir), str(backup_dir))

            shutil.move(str(staging_dir), str(target_dir))
            operation.state = OperationState.PROMOTED

            file_tree_result = cls.build_file_tree(str(target_dir))

            project.disk_size_bytes = actual_bytes
            project.file_tree = file_tree_result
            operation.state = OperationState.COMPLETED
            db.commit()

            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)

            return {
                "project_id": project.id,
                "project_uuid": project.uuid,
                "title": project.title,
                "file_tree": file_tree_result
            }

        except Exception as e:
            db.rollback()
            operation.state = OperationState.FAILED
            db.commit()
            logger.error(f"[PULL_OPERATION_FAILED] Operation {operation.id} failed: {str(e)}")
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)
            raise

    @classmethod
    def build_file_tree(cls, root_path: str, current_depth: int = 0, entry_counter: List[int] = None) -> Dict[str, Any]:
        """Recursively parses file structure, returning explicit truncation metadata when limits are exceeded."""
        if entry_counter is None:
            entry_counter = [0]

        is_truncated = False
        if current_depth > MAX_DIRECTORY_DEPTH or entry_counter[0] > MAX_ARCHIVE_ENTRIES:
            return {"tree": [], "is_truncated": True}

        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode"}
        tree = []

        try:
            for entry in os.scandir(root_path):
                if entry.name in ignore_dirs:
                    continue

                entry_counter[0] += 1
                if entry_counter[0] > MAX_ARCHIVE_ENTRIES:
                    is_truncated = True
                    break

                if entry.is_dir(follow_symlinks=False):
                    sub_result = cls.build_file_tree(entry.path, current_depth + 1, entry_counter)
                    if sub_result.get("is_truncated"):
                        is_truncated = True

                    tree.append({
                        "name": entry.name,
                        "type": "directory",
                        "children": sub_result.get("tree", [])
                    })
                else:
                    tree.append({
                        "name": entry.name,
                        "type": "file",
                        "path": os.path.relpath(entry.path, root_path).replace("\\", "/")
                    })
        except Exception as e:
            logger.error(f"[FILE_TREE_ERROR] Error scanning file tree path {root_path}: {str(e)}")

        sorted_tree = sorted(tree, key=lambda x: (x["type"] != "directory", x["name"]))
        return {"tree": sorted_tree, "is_truncated": is_truncated}

    @classmethod
    def reconcile_orphaned_storage(cls, db: Session):
        """Operation-aware reconciliation task that checks filesystem against active database state."""
        active_op_ids = {op.id for op in db.query(ProjectOperation.id).filter(
            ProjectOperation.state.in_([OperationState.RESERVED, OperationState.STAGED, OperationState.PROMOTED])
        ).all()}

        # 1. Reconcile Staging Directories
        if STAGING_ROOT.exists():
            for item in STAGING_ROOT.iterdir():
                if item.is_dir() and item.name not in active_op_ids:
                    shutil.rmtree(item, ignore_errors=True)
                    logger.info(f"[RECONCILIATION_CLEANUP] Purged orphaned staging workspace: {item}")

        # 2. Reconcile Backup Directories
        if BACKUPS_ROOT.exists():
            for item in BACKUPS_ROOT.iterdir():
                backup_id = item.name.replace("backup_", "")
                if item.is_dir() and backup_id not in active_op_ids:
                    shutil.rmtree(item, ignore_errors=True)
                    logger.info(f"[RECONCILIATION_CLEANUP] Purged orphaned backup directory: {item}")