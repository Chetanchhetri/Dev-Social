import os
import uuid
import shutil
from fastapi import UploadFile, HTTPException, status

MEDIA_DIR = os.getenv("MEDIA_DIR", "uploads")

# Allowed extensions and size limits
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE_SIZE_MB = 100  # 100 MB limit for demo uploads


class LocalStorageService:

    @staticmethod
    def _ensure_dir_exists(folder_name: str) -> str:
        target_dir = os.path.join(MEDIA_DIR, folder_name)
        os.makedirs(target_dir, exist_ok=True)
        return target_dir

    @classmethod
    def save_file(cls, file: UploadFile, subfolder: str) -> str:
        """
        Saves an uploaded file to local storage and returns its relative URL path.
        """
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        # Validation checks
        if subfolder in ["videos", "shorts"] and file_ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid video format. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
            )
        elif subfolder == "thumbnails" and file_ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image format. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )

        # Generate unique filename to prevent overwriting
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        target_dir = cls._ensure_dir_exists(subfolder)
        file_path = os.path.join(target_dir, unique_filename)

        # Stream file to disk in chunks to avoid memory bottlenecks
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )

        # Return static access URL path
        return f"/media/{subfolder}/{unique_filename}"

    @classmethod
    def delete_file(cls, relative_url_path: str) -> bool:
        """
        Deletes a file given its static URL path.
        """
        clean_path = relative_url_path.lstrip("/media/")
        full_path = os.path.join(MEDIA_DIR, clean_path)
        
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False