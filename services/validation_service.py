import logging
from typing import Dict, Any, List
from models.dto import MedicationDto, FoodDto, FrequencyDto, TaperingDto

logger = logging.getLogger(__name__)

class ValidationService:
    def __init__(self):
        self.default_prescription = {
            "diagnosis": "",
            "history": "",
            "name": "",
            "age": 0,
            "sex": "",
            "medication": [],
            "test_suggested": "",
            "test_results": "",
            "medical_notes": "",
            "followUp": None
        }
        
        self.default_medication = {
            "medicine_name": "",
            "dosage": "",
            "days": 0,
            "is_sos": False,
            "food": {
                "before_breakfast": False,
                "after_breakfast": False,
                "lunch": False,
                "dinner": False
            },
            "frequency": {
                "od": False,
                "bid": False,
                "tid": False,
                "qid": False,
                "hs": False,
                "ac": False,
                "pc": False,
                "qam": False,
                "qpm": False,
                "bs": False,
                "q6h": False,
                "q8h": False,
                "q12h": False,
                "qod": False,
                "q1w": False,
                "q2w": False,
                "q3w": False,
                "q1m": False
            },
            "tapering": None
        }
        
        self.default_tapering = {
            "frequency": "",
            "days": 0,
            "comments": ""
        }
    
    def validate_prescription_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and apply defaults to prescription data"""
        try:
            # Apply prescription-level defaults
            validated_data = {**self.default_prescription, **data}
            
            # Validate and process medication array
            medications = data.get("medication", [])
            validated_medications = []
            
            for med in medications:
                validated_med = self._validate_medication(med)
                validated_medications.append(validated_med)
            
            validated_data["medication"] = validated_medications
            
            # Ensure age is an integer
            try:
                validated_data["age"] = int(validated_data["age"]) if validated_data["age"] else 0
            except (ValueError, TypeError):
                validated_data["age"] = 0
            
            # Ensure required string fields are strings
            for field in ["diagnosis", "history", "name", "sex", "test_suggested", "test_results", "medical_notes"]:
                if not isinstance(validated_data[field], str):
                    validated_data[field] = str(validated_data[field]) if validated_data[field] is not None else ""
            
            return validated_data
            
        except Exception as e:
            logger.error(f"Error validating prescription data: {str(e)}")
            # Return default data structure if validation fails
            return self.default_prescription.copy()
    
    def _validate_medication(self, med_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual medication data"""
        try:
            # Apply medication defaults
            validated_med = {**self.default_medication, **med_data}
            
            # Validate food data
            food_data = med_data.get("food", {})
            validated_med["food"] = {**self.default_medication["food"], **food_data}
            
            # Validate frequency data
            frequency_data = med_data.get("frequency", {})
            validated_med["frequency"] = {**self.default_medication["frequency"], **frequency_data}
            
            # Validate tapering data
            tapering_data = med_data.get("tapering")
            if tapering_data and isinstance(tapering_data, list) and len(tapering_data) > 0:
                validated_tapering = []
                for tap in tapering_data:
                    validated_tap = {**self.default_tapering, **tap}
                    # Ensure frequency is a string
                    if not isinstance(validated_tap["frequency"], str):
                        validated_tap["frequency"] = ""
                    validated_tapering.append(validated_tap)
                validated_med["tapering"] = validated_tapering
            else:
                validated_med["tapering"] = None
            
            # Ensure required fields are correct types
            validated_med["medicine_name"] = str(validated_med["medicine_name"]) if validated_med["medicine_name"] else ""
            validated_med["dosage"] = str(validated_med["dosage"]) if validated_med["dosage"] else ""
            
            try:
                validated_med["days"] = int(validated_med["days"]) if validated_med["days"] else 0
            except (ValueError, TypeError):
                validated_med["days"] = 0
            
            validated_med["is_sos"] = bool(validated_med["is_sos"])
            
            return validated_med
            
        except Exception as e:
            logger.error(f"Error validating medication: {str(e)}")
            return self.default_medication.copy()
    
    def create_medication_dto(self, med_data: Dict[str, Any]) -> MedicationDto:
        """Create MedicationDto from validated data"""
        try:
            food_dto = FoodDto(**med_data["food"])
            frequency_dto = FrequencyDto(**med_data["frequency"])
            
            tapering_dtos = None
            if med_data.get("tapering"):
                tapering_dtos = [TaperingDto(**tap) for tap in med_data["tapering"]]
            
            return MedicationDto(
                medicine_name=med_data["medicine_name"],
                dosage=med_data["dosage"],
                days=med_data["days"],
                is_sos=med_data["is_sos"],
                food=food_dto,
                frequency=frequency_dto,
                tapering=tapering_dtos,
                original_name=med_data.get("original_name"),
                rejected_matches=med_data.get("rejected_matches"),
                no_match_found=med_data.get("no_match_found")
            )
            
        except Exception as e:
            logger.error(f"Error creating MedicationDto: {str(e)}")
            # Return default medication DTO
            return MedicationDto(
                medicine_name="",
                dosage="",
                days=0,
                is_sos=False,
                food=FoodDto(),
                frequency=FrequencyDto(),
                tapering=None
            ) 