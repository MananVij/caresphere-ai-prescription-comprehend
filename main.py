from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv
import logging
from contextlib import asynccontextmanager

from services.comprehend_service import ComprehendService
from models.dto import ComprehendRequest, ComprehendResponse
from services.firebase_service import FirebaseService
from services.validation_service import ValidationService

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
firebase_service = FirebaseService()
validation_service = ValidationService()
comprehend_service = ComprehendService(firebase_service, validation_service)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Comprehend AI Processing Service starting up...")
    yield
    # Shutdown
    logger.info("🛑 Comprehend AI Processing Service shutting down...")

app = FastAPI(
    title="Comprehend AI Processing Service",
    description="Internal FastAPI service for AI-powered prescription processing",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - Only allow main backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("MAIN_BACKEND_URL"),
    ],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

@app.post("/api/process", response_model=ComprehendResponse)
async def process_prescription(request: ComprehendRequest):
    """
    Internal API endpoint for AI processing only
    Called by main NestJS backend, not directly by frontend
    """
    try:
        logger.info(f"Processing prescription for doctor: {request.doctor_id}, patient: {request.patient_id}")
        # Process the prescription with AI
        result = await comprehend_service.process_prescription_ai(request)
        
        logger.info(f"AI processing completed. Success: {result.success}")
        return result
        
    except Exception as e:
        logger.error(f"Error in AI processing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"AI processing failed: {str(e)}"
        )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3002))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    ) 