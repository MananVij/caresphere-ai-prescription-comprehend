import os
import json
import logging
from typing import Dict, Any
import firebase_admin
from firebase_admin import credentials, storage
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class FirebaseService:
    def __init__(self):
        self.bucket = None
        self.executor = ThreadPoolExecutor(max_workers=3)
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # Try to load service account key
                service_account_path = os.path.join(os.getcwd(), "serviceAccountKey.json")
                
                if os.path.exists(service_account_path):
                    cred = credentials.Certificate(service_account_path)
                else:
                    # Try environment variable for service account JSON
                    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
                    if service_account_json:
                        service_account_dict = json.loads(service_account_json)
                        cred = credentials.Certificate(service_account_dict)
                    else:
                        raise ValueError("Firebase service account key not found")
                
                firebase_admin.initialize_app(cred, {
                    'storageBucket': os.getenv("FIREBASE_STORAGE_BUCKET")
                })
            
            self.bucket = storage.bucket()
            logger.info("Firebase initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise ValueError(f"Firebase initialization failed: {str(e)}")
    
    async def upload_file(
        self, 
        file_content: bytes, 
        file_path: str, 
        content_type: str,
        original_name: str
    ) -> Dict[str, Any]:
        """Upload file to Firebase Storage asynchronously"""
        try:
            # Run the upload in a thread executor to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._upload_file_sync,
                file_content,
                file_path,
                content_type,
                original_name
            )
            return result
            
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "details": {
                    "file_path": file_path,
                    "content_type": content_type,
                    "original_name": original_name
                }
            }
    
    def _upload_file_sync(
        self, 
        file_content: bytes, 
        file_path: str, 
        content_type: str,
        original_name: str
    ) -> Dict[str, Any]:
        """Synchronous file upload to Firebase Storage"""
        try:
            blob = self.bucket.blob(file_path)
            
            # Upload the file
            blob.upload_from_string(
                file_content,
                content_type=content_type
            )
            
            # Try to make the file public
            try:
                blob.make_public()
                public_url = blob.public_url
                return {
                    "success": True,
                    "url": public_url
                }
            except Exception as public_error:
                # Fallback to signed URL
                try:
                    signed_url = blob.generate_signed_url(
                        expiration="2500-01-01T00:00:00Z",
                        method="GET"
                    )
                    return {
                        "success": True,
                        "url": signed_url
                    }
                except Exception as signed_error:
                    return {
                        "success": False,
                        "error": "Failed to make file public or generate signed URL",
                        "details": {
                            "public_error": str(public_error),
                            "signed_url_error": str(signed_error),
                            "file_path": file_path,
                            "content_type": content_type,
                            "original_name": original_name
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Firebase upload error: {str(e)}")
            return {
                "success": False,
                "error": f"Firebase upload failed: {str(e)}",
                "details": {
                    "file_path": file_path,
                    "content_type": content_type,
                    "original_name": original_name,
                    "error_type": type(e).__name__
                }
            } 