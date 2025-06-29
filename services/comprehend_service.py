import os
import json
import base64
import time
import logging
from typing import Optional

import google.generativeai as genai
from models.dto import ComprehendRequest, ComprehendResponse, AIProcessingResult, ErrorDetails
from services.firebase_service import FirebaseService
from services.validation_service import ValidationService

logger = logging.getLogger(__name__)

class ComprehendService:
    def __init__(self, firebase_service: FirebaseService, validation_service: ValidationService):
        self.firebase_service = firebase_service
        self.validation_service = validation_service
        
        # Initialize Gemini AI
        api_key = os.getenv("GEMINI_GEN_AI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_GEN_AI_API_KEY is not configured")
        
        genai.configure(api_key=api_key)
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self.prompt = os.getenv("GEMINI_PROMPT", self._get_default_prompt())
        
        logger.info(f"Initialized ComprehendService with model: {self.model_name}")
    
    def _get_default_prompt(self) -> str:
        return '''Convert unstructured medical data to JSON: {
            "diagnosis": "string", 
            "history": "string", 
            "name": "string", 
            "age": "int", 
            "sex": "string", 
            "medication": [{
                "medicine_name": "string", 
                "dosage": "string", 
                "days": "int", 
                "tapering": [{
                    "frequency": "string (must be one of: od, bid, tid, qid, hs, ac, pc, qam, qpm, bs, q6h, q8h, q12h, qod, q1w, q2w, q3w, q1m)", 
                    "days": "int", 
                    "comments": "string"
                }], 
                "is_sos": "bool", 
                "food": {
                    "before_breakfast": "bool", 
                    "after_breakfast": "bool", 
                    "lunch": "bool", 
                    "dinner": "bool"
                }, 
                "frequency": {
                    "od": "bool", "bid": "bool", "tid": "bool", "qid": "bool", "hs": "bool", "ac": "bool", "pc": "bool", "qam": "bool", "qpm": "bool", "bs": "bool", "q6h": "bool", "q8h": "bool", "q12h": "bool", "qod": "bool", "q1w": "bool", "q2w": "bool", "q3w": "bool", "q1m": "bool"
                }
            }], 
            "test_suggested": "string", 
            "test_results": "string", 
            "medical_notes": "string", 
            "followUp": "string (ISO format: YYYY-MM-DD) or null if missing"
        }. Return an empty string ("") for "tapering.frequency" if missing or unclear, and null for "tapering" if not mentioned. Return an empty string ("") for unhandled or missing data. Extract medicine name and dosage separately: do not include dosage in the medicine name. Include dosage units if provided, retain prefixes (e.g., tab, syrup) in medicine names and add them to the medicine name in response, and handle abbreviations (od, bid, etc.) in frequency and add them in the frequency object instead of mapping them to meal timings.'''

    async def process_prescription_ai(self, request: ComprehendRequest) -> ComprehendResponse:
        """
        AI processing only - no database operations
        Main NestJS backend handles DB save and error logging
        """
        file_url: Optional[str] = None
        start_time = time.time()
        
        try:
            # Process file data
            if isinstance(request.file.data, bytes):
                file_content = request.file.data
                base64_data = base64.b64encode(file_content).decode('utf-8')
            else:
                base64_data = request.file.data
                file_content = base64.b64decode(base64_data)
            
            # Determine file type and processing flags
            is_handwritten_rx = False
            is_voice_rx = False
            
            if (request.file.mimetype.startswith('image/') or 
                request.file.mimetype == 'application/pdf'):
                is_handwritten_rx = True
                file_path = f"image_prescription/{request.doctor_id}/{request.patient_id}/{int(time.time())}_{request.file.originalname}"
            elif request.file.mimetype.startswith('audio/'):
                is_voice_rx = True
                file_path = f"audio_files/{request.doctor_id}/{request.patient_id}/{int(time.time())}_{request.file.originalname}"
            else:
                raise ValueError("Unsupported file type")
            
            # Upload file to Firebase
            upload_result = await self.firebase_service.upload_file(
                file_content=file_content,
                file_path=file_path,
                content_type=request.file.mimetype,
                original_name=request.file.originalname
            )
            
            if not upload_result["success"]:
                return ComprehendResponse(
                    success=False,
                    processing_time=int((time.time() - start_time) * 1000),
                    error=ErrorDetails(
                        message=f"Firebase upload failed: {upload_result['error']}",
                        type="FirebaseUploadError",
                        context={
                            "doctor_id": request.doctor_id,
                            "patient_id": request.patient_id,
                            "file_name": request.file.originalname,
                            "mimetype": request.file.mimetype,
                            "firebase_details": upload_result.get("details")
                        }
                    )
                )
            
            file_url = upload_result["url"]
            
            # Process with Gemini AI
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "max_output_tokens": 8192,
                    "temperature": 0,
                    "top_p": 0.95
                }
            )
            
            # Prepare file data for Gemini
            file_data = {
                "mime_type": request.file.mimetype,
                "data": base64_data
            }
            
            # Generate content
            response = await self._generate_content_async(model, file_data, self.prompt)
            
            # Parse JSON response
            json_string = response.replace('```json', '').replace('```', '').strip()
            parsed_json = json.loads(json_string)
            
            # Validate prescription data
            validated_data = self.validation_service.validate_prescription_data(parsed_json)
            
            # Return AI processing result (no DB operations)
            ai_result = AIProcessingResult(
                validated_data=validated_data,
                file_url=file_url,
                is_handwritten_rx=is_handwritten_rx,
                is_voice_rx=is_voice_rx
            )
            
            return ComprehendResponse(
                success=True,
                processing_time=int((time.time() - start_time) * 1000),
                ai_result=ai_result
            )
            
        except Exception as e:
            logger.error(f"Error in AI processing: {str(e)}")
            return ComprehendResponse(
                success=False,
                processing_time=int((time.time() - start_time) * 1000),
                error=ErrorDetails(
                    message=str(e),
                    type=type(e).__name__,
                    context={
                        "doctor_id": request.doctor_id,
                        "patient_id": request.patient_id,
                        "file_name": request.file.originalname,
                        "mimetype": request.file.mimetype,
                        "file_url": file_url
                    }
                )
            )
    
    async def _generate_content_async(self, model, file_data, prompt_text):
        """Generate content using Gemini AI asynchronously"""
        try:
            # Create the content parts
            parts = [
                {
                    "inline_data": file_data
                },
                {
                    "text": prompt_text
                }
            ]
            
            # Generate content
            response = model.generate_content(parts)
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating content with Gemini: {str(e)}")
            raise 