import os
import json
import base64
import time
import logging
from typing import Optional

import google.generativeai as genai
from models.dto import ComprehendRequest, ComprehendResponse, AIProcessingResult, ErrorDetails, BillRequest, BillResponse
from services.firebase_service import FirebaseService
from services.validation_service import ValidationService

logger = logging.getLogger(__name__)

class ComprehendService:
    def __init__(self, firebase_service: FirebaseService, validation_service: ValidationService):
        self.firebase_service = firebase_service
        self.validation_service = validation_service
        
        # Initialize Gemini AI
        api_key = os.getenv("GEMINI_GEN_AI_API_KEY")
        bill_model = os.getenv("GEMINI_BILL_MODEL")
        prescription_model = os.getenv("GEMINI_PRESCRIPTION_MODEL")
        bill_prompt = os.getenv("GEMINI_BILL_PROMPT")
        prescription_prompt = os.getenv("GEMINI_PRESCRIPTION_PROMPT")
        
        if not api_key or not bill_model or not prescription_model or not bill_prompt or not prescription_prompt:
            raise ValueError("Environment variables not configured")
        
        genai.configure(api_key=api_key)
        
        self.prescription_model = prescription_model
        self.bill_model = bill_model
        self.prescription_prompt = prescription_prompt
        self.bill_prompt = bill_prompt
        
        logger.info(f"Initialized ComprehendService with prescription model: {self.prescription_model}, bill model: {self.bill_model}")

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
                model_name=self.prescription_model,
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
            response = await self._generate_content_async(model, file_data, self.prescription_prompt)
            
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

    async def process_bill_ai(self, request: BillRequest) -> BillResponse:
        """
        AI processing for supplier medicine bills - no database operations
        Main NestJS backend handles DB save and error logging
        """
        try:
            # Process file data
            if isinstance(request.file, bytes):
                file_content = request.file
                base64_data = base64.b64encode(file_content).decode('utf-8')
            else:
                base64_data = request.file
                file_content = base64.b64decode(base64_data)

            if not request.mimetype.startswith('image/'):
                raise ValueError("Unsupported file type for supplier bill processing")
            
            # Process with Gemini AI
            model = genai.GenerativeModel(
                model_name=self.bill_model,
                generation_config={
                    "max_output_tokens": 8192,
                    "temperature": 0,
                    "top_p": 0.95
                }
            )
            
            # Prepare file data for Gemini
            file_data = {
                "mime_type": request.mimetype,
                "data": base64_data
            }
            
            # Generate content
            response = await self._generate_content_async(model, file_data, self.bill_prompt)
            
            # Parse JSON response
            json_string = response.replace('```json', '').replace('```', '').strip()
            parsed_json = json.loads(json_string)
            
            # Validate supplier bill data
            validated_data = self.validation_service.validate_supplier_bill_data(parsed_json)
            
            # Return AI processing result (no DB operations, no file upload)
            return BillResponse(
                success=True,
                bill_result=validated_data
            )
            
        except Exception as e:
            logger.error(f"Error in supplier bill AI processing: {str(e)}")
            return BillResponse(
                success=False,
                error=ErrorDetails(
                    message=str(e),
                    type=type(e).__name__,
                    context={
                        "doctor_id": request.doctor_id,
                        "clinic_id": request.clinic_id,
                        "file_name": "supplier_bill.jpg",
                        "mimetype": request.mimetype,
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