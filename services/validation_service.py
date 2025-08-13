import logging
from typing import Dict, Any, List
from models.dto import MedicationDto, FoodDto, FrequencyDto, TaperingDto, SupplierDto, BuyFromSupplierMedicineDto, SupplierBillDto

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

        # Default supplier bill structure
        self.default_supplier_bill = {
            "supplier": {
                "name": "",
                "gst_number": "",
                "address_line1": "",
                "address_line2": "",
                "city": "",
                "state": "",
                "contact_person_name": "",
                "phone": "",
                "email": ""
            },
            "bill_number": "",
            "medicines": []
        }

        # Default supplier medicine structure
        self.default_supplier_medicine = {
            "medicine_name": "",
            "dosage": "",
            "quantity": 0,
            "mrp": 0.0,
            "buying_price": 0.0,
            "selling_price": 0.0,
            "expiry_date": "",
            "batch_number": "",
            "manufacturer": ""
        }

        self.default_supplier = {
            "name": "",
            "gst_number": "",
            "address_line1": "",
            "address_line2": "",
            "city": "",
            "state": "",
            # Clinic contact info
            "phone": "",
            "email": "",
            # Contact person info
            "contact_person_name": "",
            "contact_person_phone": ""
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

    def validate_supplier_bill_data(self, data: Dict[str, Any]) -> SupplierBillDto:
        """Validate and apply defaults to supplier bill data"""
        try:
            # Apply supplier bill-level defaults
            validated_data = {**self.default_supplier_bill, **data}
            
            # Validate supplier data
            supplier_data = data.get("supplier", {})
            validated_data["supplier"] = self._validate_supplier(supplier_data)
            
            # Validate and process medicines array
            medicines = data.get("medicines", [])
            validated_medicines = []
            
            for med in medicines:
                validated_med = self._validate_supplier_medicine(med)
                validated_medicines.append(validated_med)
            
            validated_data["medicines"] = validated_medicines
            
            # Ensure required string fields are strings
            validated_data["bill_number"] = str(validated_data["bill_number"]) if validated_data["bill_number"] else ""
            
            # Create and return the DTO
            return self.create_supplier_bill_dto(validated_data)
            
        except Exception as e:
            logger.error(f"Error validating supplier bill data: {str(e)}")
            # Return default data structure if validation fails
            return self.create_supplier_bill_dto(self.default_supplier_bill.copy())
    
    def _validate_supplier_medicine(self, med_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual supplier medicine data"""
        try:
            # Apply medicine defaults
            validated_med = {**self.default_supplier_medicine, **med_data}
            
            # Ensure required fields are correct types
            validated_med["medicine_name"] = str(validated_med["medicine_name"]) if validated_med["medicine_name"] else ""
            validated_med["dosage"] = str(validated_med["dosage"]) if validated_med["dosage"] else ""
            validated_med["expiry_date"] = str(validated_med["expiry_date"]) if validated_med["expiry_date"] else ""
            
            try:
                validated_med["quantity"] = int(validated_med["quantity"]) if validated_med["quantity"] else 0
            except (ValueError, TypeError):
                validated_med["quantity"] = 0
            
            try:
                validated_med["mrp"] = float(validated_med["mrp"]) if validated_med["mrp"] else 0.0
            except (ValueError, TypeError):
                validated_med["mrp"] = 0.0
            
            try:
                validated_med["buying_price"] = float(validated_med["buying_price"]) if validated_med["buying_price"] else 0.0
            except (ValueError, TypeError):
                validated_med["buying_price"] = 0.0
            
            try:
                validated_med["selling_price"] = float(validated_med["selling_price"]) if validated_med["selling_price"] else 0.0
            except (ValueError, TypeError):
                validated_med["selling_price"] = 0.0
            
            # Set selling_price equal to mrp if not provided
            if validated_med["selling_price"] == 0.0 and validated_med["mrp"] > 0.0:
                validated_med["selling_price"] = validated_med["mrp"]
            
            validated_med["batch_number"] = str(validated_med["batch_number"]) if validated_med["batch_number"] else ""
            validated_med["manufacturer"] = str(validated_med["manufacturer"]) if validated_med["manufacturer"] else ""
            
            return validated_med
            
        except Exception as e:
            logger.error(f"Error validating supplier medicine: {str(e)}")
            return self.default_supplier_medicine.copy()

    def _validate_supplier(self, supplier_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate supplier data"""
        try:
            # Apply supplier defaults
            validated_supplier = {**self.default_supplier, **supplier_data}
            
            # Ensure all fields are strings
            for field in ["name", "gst_number", "address_line1", "address_line2", "city", "state", "phone", "email", "contact_person_name", "contact_person_phone"]:
                if not isinstance(validated_supplier[field], str):
                    validated_supplier[field] = str(validated_supplier[field]) if validated_supplier[field] is not None else ""
            
            return validated_supplier
            
        except Exception as e:
            logger.error(f"Error validating supplier: {str(e)}")
            return self.default_supplier.copy()

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

    def create_supplier_bill_dto(self, bill_data: Dict[str, Any]) -> SupplierBillDto:
        """Create SupplierBillDto from validated data"""
        try:
            supplier_dto = SupplierDto(**bill_data["supplier"])
            medicines_dtos = [BuyFromSupplierMedicineDto(**med) for med in bill_data["medicines"]]
            
            return SupplierBillDto(
                supplier=supplier_dto,
                bill_number=bill_data["bill_number"],
                medicines=medicines_dtos
            )
            
        except Exception as e:
            logger.error(f"Error creating SupplierBillDto: {str(e)}")
            # Return default supplier bill DTO
            return SupplierBillDto(
                supplier=SupplierDto(name=""),
                bill_number="",
                medicines=[]
            ) 