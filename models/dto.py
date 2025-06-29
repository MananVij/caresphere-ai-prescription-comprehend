from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union

class FileData(BaseModel):
    data: Union[bytes, str]  # Can be bytes or base64 string
    originalname: str
    mimetype: str
    size: int

class ComprehendRequest(BaseModel):
    file: FileData
    doctor_id: str
    patient_id: str
    clinic_id: int
    appointment_id: str

class TaperingDto(BaseModel):
    frequency: str
    days: int
    comments: str

class FoodDto(BaseModel):
    before_breakfast: bool = False
    after_breakfast: bool = False
    lunch: bool = False
    dinner: bool = False

class FrequencyDto(BaseModel):
    od: bool = False
    bid: bool = False
    tid: bool = False
    qid: bool = False
    hs: bool = False
    ac: bool = False
    pc: bool = False
    qam: bool = False
    qpm: bool = False
    bs: bool = False
    q6h: bool = False
    q8h: bool = False
    q12h: bool = False
    qod: bool = False
    q1w: bool = False
    q2w: bool = False
    q3w: bool = False
    q1m: bool = False

class MedicationDto(BaseModel):
    medicine_name: str
    dosage: str
    days: int
    is_sos: bool = False
    food: FoodDto
    frequency: FrequencyDto
    tapering: Optional[List[TaperingDto]] = None

class AIProcessingResult(BaseModel):
    """AI processing result - data only, no DB operations"""
    validated_data: Dict[str, Any]  # The validated prescription data
    file_url: str
    is_handwritten_rx: bool
    is_voice_rx: bool

class ErrorDetails(BaseModel):
    message: str
    type: str
    context: Dict[str, Any]

class ComprehendResponse(BaseModel):
    """Response from AI processing service"""
    success: bool
    processing_time: int
    ai_result: Optional[AIProcessingResult] = None
    error: Optional[ErrorDetails] = None 