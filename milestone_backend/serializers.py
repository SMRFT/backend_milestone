import json
from rest_framework import serializers
from .models import (
    Registration, PatientAssessment, EmployeeRegistration, DevelopmentalTask, 
    PediatricAssessment, SkillTestResult, TherapyBilling, OthersBilling, 
    MCHATResponse, ReferralDoctor, ChildLanguageAssessment, DevelopmentalScreeningTask, 
    CBCL, ConsultingDoctor, PatientAttendance, HistoryRecordingSheet, 
    ClinicalPsychologyAssessment, OccupationalTherapyAssessment, SpeechTherapyAssessment, 
    PhysiotherapyAssessment, AssessmentAnalysis, GoalsAssessment, leaveform, 
    DevelopmentGoals, TherapyDetails, GoalDomain, GoalLevel, GoalLibrary, AppointmentSchedule, ActivityLibrary,
    BehavioralObservationOption
)
from djongo.models import ObjectIdField

class ObjectIdField(serializers.Field):
    def to_representation(self, value):
        return str(value)
    def to_internal_value(self, data):
        return ObjectId(data)

def safe_parse_json(value):
    if not isinstance(value, str):
        return value
    
    # 1. Try standard JSON parsing
    try:
        parsed = json.loads(value)
        if isinstance(parsed, str):
            return safe_parse_json(parsed)
        return parsed
    except (ValueError, TypeError):
        pass

    # 2. Try handling Python representation strings (e.g. OrderedDict, python dicts/lists)
    if 'OrderedDict' in value or 'dict' in value or '(' in value or '[' in value:
        from collections import OrderedDict
        try:
            safe_ns = {
                'OrderedDict': OrderedDict,
                'dict': dict,
                'list': list,
                'tuple': tuple
            }
            parsed = eval(value, {"__builtins__": None}, safe_ns)
            
            def convert_to_json_types(obj):
                if isinstance(obj, OrderedDict) or isinstance(obj, dict):
                    return {k: convert_to_json_types(v) for k, v in obj.items()}
                elif isinstance(obj, list) or isinstance(obj, tuple):
                    return [convert_to_json_types(i) for i in obj]
                else:
                    return obj
            
            return convert_to_json_types(parsed)
        except Exception:
            pass

    # 3. Fallback: try converting python single quote representation to valid JSON
    try:
        repr_val = value.replace("'", '"')
        repr_val = repr_val.replace(': True', ': true').replace(': False', ': false').replace(': None', ': null')
        repr_val = repr_val.replace(', True', ', true').replace(', False', ', false').replace(', None', ', null')
        repr_val = repr_val.replace('[True', '[true').replace('[False', '[false').replace('[None', '[null')
        parsed = json.loads(repr_val)
        if isinstance(parsed, str):
            return safe_parse_json(parsed)
        return parsed
    except (ValueError, TypeError):
        pass

    return value

class SafeJsonFieldsMixin:
    json_fields = []

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data_copy = data.copy()
        else:
            data_copy = dict(data)

        for field in self.json_fields:
            if field in data_copy:
                data_copy[field] = safe_parse_json(data_copy[field])

        return super().to_internal_value(data_copy)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Convert ObjectId to string if present
        if 'id' in data and data['id'] is not None:
            data['id'] = str(data['id'])
        if '_id' in data and data['_id'] is not None:
            data['_id'] = str(data['_id'])
            
        for field in self.json_fields:
            if field in data:
                data[field] = safe_parse_json(data[field])

        return data

class RegistrationSerializer(serializers.ModelSerializer):
    # Handle ObjectId serialization
    id = serializers.CharField(read_only=True)  # Override the ObjectId field
    
    class Meta:
        model = Registration
        fields = '__all__'
        # Make audit fields read-only since we'll set them programmatically
        read_only_fields = ['id', 'created_by', 'created_date', 'lastmodified_date']

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data_copy = data.copy()
        else:
            data_copy = dict(data)

        for field in ['age', 'reason_for_visit', 'source_of_referral']:
            if field in data_copy:
                data_copy[field] = safe_parse_json(data_copy[field])

        return super().to_internal_value(data_copy)

    def to_representation(self, instance):
        """Custom serialization to handle ObjectId and parse stringified JSON fields"""
        data = super().to_representation(instance)
        
        # Convert ObjectId to string if present
        if 'id' in data and data['id'] is not None:
            data['id'] = str(data['id'])
            
        for field in ['age', 'reason_for_visit', 'source_of_referral']:
            if field in data:
                data[field] = safe_parse_json(data[field])

        return data
    
    def create(self, validated_data):
        # Get the employee_id from the context (passed from the view)
        employee_id = self.context.get('employee_id')
        
        # Set the created_by field
        if employee_id:
            validated_data['created_by'] = employee_id
            
        return super().create(validated_data)

class EmployeeRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeRegistration
        fields = '__all__'

# If you also have PatientAssessmentSerializer, here's the fix for that too:
class PatientAssessmentSerializer(serializers.ModelSerializer):
    # Handle ObjectId serialization
    id = serializers.CharField(read_only=True)
    
    class Meta:
        model = PatientAssessment  # Assuming this is your model name
        fields = '__all__'
        # Make audit fields read-only since we'll set them programmatically
        read_only_fields = ['id', 'created_by', 'created_date', 'lastmodified_date']

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data_copy = data.copy()
        else:
            data_copy = dict(data)

        for field in ['age', 'assessments']:
            if field in data_copy:
                data_copy[field] = safe_parse_json(data_copy[field])

        return super().to_internal_value(data_copy)
    
    def to_representation(self, instance):
        """Custom serialization to handle ObjectId and parse stringified JSON fields"""
        data = super().to_representation(instance)
        
        # Convert ObjectId to string if present
        if 'id' in data and data['id'] is not None:
            data['id'] = str(data['id'])
            
        for field in ['age', 'assessments']:
            if field in data:
                data[field] = safe_parse_json(data[field])

        return data
    
    def create(self, validated_data):
        # Get the employee_id from the context (passed from the view)
        employee_id = self.context.get('employee_id')
        
        # Set the created_by field
        if employee_id:
            validated_data['created_by'] = employee_id
            
        return super().create(validated_data)

class PediatricAssessmentSerializer(SafeJsonFieldsMixin, serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    json_fields = ['age', 'developmental_history']
    
    class Meta:
       
        model = PediatricAssessment
        fields = '__all__'

from bson import ObjectId
from decimal import Decimal
import os
from pymongo import MongoClient
from bson.decimal128 import Decimal128
from pymongo import DESCENDING, MongoClient
from datetime import datetime ,timedelta ,date

_mongo_client_serialization = None
_attendance_col_serialization = None
def get_attendance_col():
    global _mongo_client_serialization, _attendance_col_serialization
    if _attendance_col_serialization is None:
        mongo_uri = os.environ.get("GLOBAL_DB_HOST")
        db_name = os.environ.get("MILESTONE_DB_NAME", "Milestone")
        if mongo_uri:
            _mongo_client_serialization = MongoClient(mongo_uri)
            db = _mongo_client_serialization[db_name]
            _attendance_col_serialization = db["milestone_backend_patientattendance"]
    return _attendance_col_serialization
def clean_decimal_value(value):
    if isinstance(value, Decimal128):
        return value.to_decimal()
    try:
        if value is None: return Decimal(0)
        return Decimal(str(value)) # str() to handle floats safely for Decimal
    except:
        return Decimal(0)

class TherapyBillingSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    created_date = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S", read_only=True
    )
    # Return the entire PatientAttendance row
    attendance_info = serializers.SerializerMethodField()
    # Return the entire Registration row
    patient_info = serializers.SerializerMethodField()
    def get_id(self, obj):
        if hasattr(obj, 'id') and isinstance(obj.id, ObjectId):
            return str(obj.id)
        return obj.id
    class Meta:
        model = TherapyBilling
        fields = "__all__"  # attendance_info will automatically append
        read_only_fields = [
            'created_by',
            'created_date',
            'lastmodified_date',
            'bill_date'
        ]
    def validate_amount_paid(self, value):
        if value < 1:
            raise serializers.ValidationError("Bill amount paid must be at least 1.")
        return value

    def create(self, validated_data):
        employee_id = self.context.get('employee_id')
        if employee_id:
            validated_data['created_by'] = employee_id
        return super().create(validated_data)
    def get_attendance_info(self, obj):
        """
        Match TherapyBilling → PatientAttendance by:
        - registration_number
        - attendance_date
        Return full Attendance data as dict.
        Using direct PyMongo to avoid JSONField mixed-type issues.
        """
        col = get_attendance_col()
        if not col or not obj.attendance_date:
            return None
        # Create date range for the query (Date in Mongo is usually ISODate)
        start_date = datetime.combine(obj.attendance_date, datetime.min.time())
        end_date = start_date + timedelta(days=1)
        attendance = col.find_one({
            "registration_number": obj.registration_number,
            "attendance_date": {"$gte": start_date, "$lt": end_date}
        })
        if attendance:
            # Helper to safely get list from potentially stringified JSON in DB
            def safe_get_list(key):
                val = attendance.get(key, [])
                if isinstance(val, str):
                    try:
                        return json.loads(val)
                    except:
                        return []
                return val
            return {
                "attendance_id": str(attendance.get("_id", "")),
                "attendance_date": attendance.get("attendance_date"),
                "session": attendance.get("session"),
                "therapy_details": safe_get_list("therapy_details"),
                "therapy_charge": clean_decimal_value(attendance.get("therapy_charge", 0)),
                "discount": clean_decimal_value(attendance.get("discount", 0)),
                "discount_remarks": attendance.get("discount_remarks", ""),
                "not_attending": clean_decimal_value(attendance.get("not_attending", 0)),
                "not_attending_details": safe_get_list("not_attending_details"),
                "extra_attending": clean_decimal_value(attendance.get("extra_attending", 0)),
                "extra_attending_details": safe_get_list("extra_attending_details"),
                "total_amount": clean_decimal_value(attendance.get("total_amount", 0)),
                "total_amount_paid": clean_decimal_value(attendance.get("total_amount_paid", 0)),
                "bill_details": safe_get_list("bill_details"),
                "consultant_doctor": safe_get_list("consultant_doctor"),
                "is_active": attendance.get("is_active", True),
                "is_approved": attendance.get("is_approved", False)
            }
        return None
    def get_patient_info(self, obj):
        # Match Registration by registration_number
        if not obj.registration_number:
            return None
        patient = Registration.objects.filter(registration_number=obj.registration_number).first()
        if patient:
            return RegistrationSerializer(patient).data
        return None
    
class OthersBillingSerializer(SafeJsonFieldsMixin, serializers.ModelSerializer):
    date = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False)
    id = serializers.SerializerMethodField()  # Convert ObjectId to string

    def get_id(self, obj):
        return str(obj.id) if isinstance(obj.id, ObjectId) else obj.id

    json_fields = ['age', 'others_items']

    class Meta:
        model = OthersBilling
        fields = "__all__"
        # Make audit fields read-only since we'll set them programmatically
        read_only_fields = ['created_by', 'created_date', 'lastmodified_date']
    
    def create(self, validated_data):
        # Get the employee_id from the context (passed from the view)
        employee_id = self.context.get('employee_id')
        
        # Set the created_by field
        if employee_id:
            validated_data['created_by'] = employee_id
            
        return super().create(validated_data)

from rest_framework import serializers
from .models import MCHATResponse

class MCHATResponseSerializer(SafeJsonFieldsMixin, serializers.ModelSerializer):
    json_fields = ['age', 'question']
    class Meta:
        model = MCHATResponse
        fields = ['registration_number','patient_name', 'age', 'sex', 'question', 'score','riskLevel']

class ReferralDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralDoctor
        fields = "__all__"
        read_only_fields = ['referral_id', 'created_by', 'created_date', 'lastmodified_date']
    
    def create(self, validated_data):
        employee_id = self.context.get('employee_id')
        if employee_id:
            validated_data['created_by'] = employee_id
        return super().create(validated_data)

class ConsultingDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultingDoctor
        fields = "__all__"
        read_only_fields = ['id', 'created_by', 'created_date', 'lastmodified_date']  # Add other auto fields as needed
    
    def create(self, validated_data):
        # Get the auth_user_id from context and set it as created_by
        auth_user_id = self.context.get('auth_user_id')
        if auth_user_id:
            validated_data['created_by'] = auth_user_id
        return super().create(validated_data)

# serializers.py
from rest_framework import serializers
from .models import ChildLanguageAssessment

class ChildLanguageAssessmentSerializer(SafeJsonFieldsMixin, serializers.ModelSerializer):
    json_fields = ['natalhistory', 'developmentalhistory', 'socialemotionalbehavior', 'prerequisitesforspeech', 'oralperipheralmechanism', 'vegetativeskills', 'communicationprofile']
    class Meta:
        model = ChildLanguageAssessment
        fields = '__all__'

# serializers.py

from rest_framework import serializers
from .models import DevelopmentalScreeningTask

class DevelopmentalScreeningTaskSerializer(SafeJsonFieldsMixin, serializers.ModelSerializer):
    json_fields = ['tasks']
    class Meta:
        model = DevelopmentalScreeningTask
        fields = '__all__'

from rest_framework import serializers
from .models import CBCL
from bson import ObjectId  # Import to handle MongoDB ObjectId

class CBCLSerializer(SafeJsonFieldsMixin, serializers.ModelSerializer):
    id = serializers.SerializerMethodField()  # Add this field
    json_fields = ['age', 'table1', 'table2', 'table3', 'table4', 'table5', 'table6', 'table7']

    class Meta:
        model = CBCL
        fields = '__all__'

    def get_id(self, obj):
        """ Convert MongoDB ObjectId to string before serialization """
        return str(obj.id) if isinstance(obj.id, ObjectId) else obj.id

# serializers.py
from rest_framework import serializers
from .models import PatientAttendance
from bson import ObjectId

class ObjectIdField(serializers.Field):
    def to_representation(self, value):
        return str(value)  # Convert ObjectId to string

    def to_internal_value(self, data):
        return ObjectId(data)

from rest_framework import serializers
from .models import PatientAttendance, DailyTimeSlot, PatientSessionAttendance

class PatientAttendanceSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = PatientAttendance
        fields =  '__all__' # ['id', 'registration_number', 'date', 'session', 'therapy_charge']

from rest_framework import serializers
from .models import HistoryRecordingSheet

def get_demographics_by_registration(registration_number, ref_date=None):
    demographics = {
        "dob": "—",
        "father": "—",
        "mother": "—",
        "mobile": "—",
        "address": "—",
        "age": "—"
    }
    if not registration_number:
        return demographics
    try:
        from .models import Registration
        patient = Registration.objects.filter(registration_number=registration_number).first()
        if patient:
            if patient.dob:
                if hasattr(patient.dob, 'strftime'):
                    demographics["dob"] = patient.dob.strftime('%Y-%m-%d')
                else:
                    demographics["dob"] = str(patient.dob)
            else:
                demographics["dob"] = "—"
                
            demographics["father"] = patient.father_name or "—"
            demographics["mother"] = patient.mother_name or "—"
            
            mobile = patient.father_phone_number or patient.mother_phone_number
            if not mobile and hasattr(patient, 'phone_number'):
                mobile = patient.phone_number
            demographics["mobile"] = mobile or "—"
            
            demographics["address"] = patient.address or "—"
            
            # Calculate/format age
            if patient.dob and ref_date:
                from datetime import datetime, date
                try:
                    dob = patient.dob
                    if isinstance(dob, str):
                        dob = datetime.strptime(dob.split('T')[0], '%Y-%m-%d').date()
                    elif isinstance(dob, datetime):
                        dob = dob.date()
                    
                    target_date = ref_date
                    if isinstance(target_date, str):
                        target_date = datetime.strptime(target_date.split('T')[0], '%Y-%m-%d').date()
                    elif isinstance(target_date, datetime):
                        target_date = target_date.date()
                    
                    years = target_date.year - dob.year - ((target_date.month, target_date.day) < (dob.month, dob.day))
                    if target_date.day >= dob.day:
                        months = target_date.month - dob.month
                    else:
                        months = target_date.month - dob.month - 1
                    if months < 0:
                        months += 12
                    
                    parts = []
                    if years > 0:
                        parts.append(f"{years} Years")
                    if months > 0:
                        parts.append(f"{months} Months")
                    demographics["age"] = " ".join(parts) if parts else "0 Months"
                except Exception as e:
                    print("Error calculating age:", e)
            
            if demographics["age"] == "—" and patient.age:
                age_val = patient.age
                if isinstance(age_val, str):
                    try:
                        import json
                        age_val = json.loads(age_val)
                    except:
                        pass
                if isinstance(age_val, dict):
                    parts = []
                    year = age_val.get("year") or age_val.get("years")
                    if year is not None:
                        parts.append(f"{year} Years")
                    month = age_val.get("months") or age_val.get("month")
                    if month is not None:
                        parts.append(f"{month} Months")
                    if parts:
                        demographics["age"] = " ".join(parts)
                    else:
                        demographics["age"] = str(age_val)
                else:
                    demographics["age"] = str(age_val)
    except Exception as e:
        print(f"Error fetching demographics for registration {registration_number}: {e}")
    return demographics


def get_employee_details(employee_id):
    details = {
        "created_by_name": "Ms. Sivashankari",
        "created_by_qualification": "",
        "created_by_designation": "",
        "created_by_signature": ""
    }
    if not employee_id:
        return details
    try:
        import os
        from pymongo import MongoClient
        mongo_uri = os.environ.get("GLOBAL_DB_HOST")
        
        client = MongoClient(mongo_uri)
            
        db = client["Global"]
        col = db["backend_diagnostics_profile"]
        
        emp_id_str = str(employee_id).strip()
        or_list = [
            {"employeeId": emp_id_str},
            {"employee_id": emp_id_str},
            {"user_id": emp_id_str},
            {"id": emp_id_str}
        ]
        if emp_id_str.isdigit():
            emp_id_int = int(emp_id_str)
            or_list.extend([
                {"employeeId": emp_id_int},
                {"employee_id": emp_id_int},
                {"user_id": emp_id_int},
                {"id": emp_id_int}
            ])
            
        doc = col.find_one({"$or": or_list})
        if doc:
            # Name
            name = doc.get("employeeName") or doc.get("name") or doc.get("full_name") or doc.get("fullName") or ""
            name = str(name).strip()
            gender = (doc.get("gender") or "").strip().lower()
            if name and not any(name.startswith(p) for p in ["Ms. ", "Mrs. ", "Mr. ", "Dr. ", "Ms.", "Mrs.", "Mr.", "Dr."]):
                if gender == "female":
                    name = f"Ms. {name}"
                elif gender == "male":
                    name = f"Mr. {name}"
            if name:
                details["created_by_name"] = name
            
            # Qualifications
            quals = doc.get("qualifications") or doc.get("qualification") or []
            qual_list = []
            if isinstance(quals, list):
                for q in quals:
                    if isinstance(q, dict) and (q.get("degree") or q.get("title") or q.get("name")):
                        qual_list.append((q.get("degree") or q.get("title") or q.get("name")).strip())
                    elif isinstance(q, str) and q.strip():
                        qual_list.append(q.strip())
            elif isinstance(quals, str) and quals.strip():
                qual_list.append(quals.strip())

            if qual_list:
                details["created_by_qualification"] = ", ".join(qual_list)
            else:
                details["created_by_qualification"] = ""
            
            # Signature Image / URL
            sig = doc.get("signature") or doc.get("uploadSignature") or doc.get("signature_url") or doc.get("employeeSignature") or doc.get("upload_signature") or doc.get("signaturePath") or ""
            if sig:
                details["created_by_signature"] = str(sig).strip()

            # Designation
            if doc.get("designation"):
                details["created_by_designation"] = str(doc.get("designation")).strip()
                
            if not details.get("created_by_designation"):
                try:
                    from .models import ConsultingDoctor
                    doc_cd = ConsultingDoctor.objects.filter(employee_id=emp_id_str).first()
                    if doc_cd and doc_cd.designation:
                        details["created_by_designation"] = doc_cd.designation.strip()
                except Exception as e:
                    print(f"Error querying ConsultingDoctor via Django ORM: {e}")

                if not details.get("created_by_designation"):
                    try:
                        db_milestone = client[os.environ.get("MILESTONE_DB_NAME", "Milestone")]
                        col_cd = db_milestone["milestone_backend_consultingdoctor"]
                        doc_cd = col_cd.find_one({"$or": [{"employee_id": emp_id_str}, {"employee_id": int(emp_id_str) if emp_id_str.isdigit() else emp_id_str}]})
                        if doc_cd and doc_cd.get("designation"):
                            details["created_by_designation"] = doc_cd["designation"].strip()
                    except Exception as e:
                        print(f"Error querying milestone_backend_consultingdoctor via PyMongo: {e}")
        else:
            # Profile not found by employeeId in backend_diagnostics_profile, fallback to ConsultingDoctor
            details["created_by_qualification"] = ""
            details["created_by_designation"] = ""
            
            try:
                from .models import ConsultingDoctor
                doc_cd = ConsultingDoctor.objects.filter(employee_id=emp_id_str).first()
                if doc_cd:
                    if doc_cd.name:
                        details["created_by_name"] = doc_cd.name.strip()
                    if doc_cd.designation:
                        details["created_by_designation"] = doc_cd.designation.strip()
            except Exception as e:
                print(f"Error querying ConsultingDoctor: {e}")
                
            if not details.get("created_by_name"):
                try:
                    db_milestone = client[os.environ.get("MILESTONE_DB_NAME", "Milestone")]
                    col_cd = db_milestone["milestone_backend_consultingdoctor"]
                    doc_cd = col_cd.find_one({"$or": [{"employee_id": emp_id_str}, {"employee_id": int(emp_id_str) if emp_id_str.isdigit() else emp_id_str}]})
                    if doc_cd:
                        if doc_cd.get("name"):
                            details["created_by_name"] = doc_cd["name"].strip()
                        if doc_cd.get("designation"):
                            details["created_by_designation"] = doc_cd["designation"].strip()
                except Exception as e:
                    print(f"Error querying milestone_backend_consultingdoctor: {e}")
    except Exception as e:
        print(f"Error fetching employee details for empid {employee_id}: {e}")
    return details


class HistoryRecordingSheetSerializer(SafeJsonFieldsMixin, serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    json_fields = ['identification_data', 'demographic_data', 'presenting_complaints', 'history_of_present_illness', 'family_history', 'personal_history', 'natalandneanatal_history', 'postnatal_history', 'developmental_history', 'scholastic_history', 'play_history', 'general_history']
    class Meta:
        model = HistoryRecordingSheet
        fields =  '__all__' 

    def to_representation(self, instance):
        data = super().to_representation(instance)
        reg_num = data.get("registration_number")
        
        demo = get_demographics_by_registration(reg_num)
        
        # Identification data fallback
        id_data = data.get("identification_data") or {}
        if isinstance(id_data, str):
            try:
                import json
                id_data = json.loads(id_data)
            except:
                id_data = {}
        
        from .models import Registration
        if not id_data.get("name") or id_data.get("name") == "N/A":
            try:
                patient = Registration.objects.filter(registration_number=reg_num).first()
                if patient:
                    id_data["name"] = patient.name_of_child
            except:
                pass
        
        if not id_data.get("dob") or id_data.get("dob") == "—" or id_data.get("dob") == "N/A":
            id_data["dob"] = demo.get("dob") or "—"
            
        if not id_data.get("age_sex") or id_data.get("age_sex") == "—" or id_data.get("age_sex") == "N/A":
            age_str = demo.get("age") or "—"
            sex_str = "—"
            try:
                patient = Registration.objects.filter(registration_number=reg_num).first()
                if patient:
                    sex_str = patient.sex
            except:
                pass
            id_data["age_sex"] = f"{age_str} / {sex_str}" if sex_str != "—" else age_str
        
        data["identification_data"] = id_data
        
        # Demographic data fallback
        demo_data = data.get("demographic_data") or {}
        if isinstance(demo_data, str):
            try:
                import json
                demo_data = json.loads(demo_data)
            except:
                demo_data = {}
        
        if not demo_data.get("father") or demo_data.get("father") == "—" or demo_data.get("father") == "N/A":
            demo_data["father"] = demo.get("father") or "—"
        if not demo_data.get("mother") or demo_data.get("mother") == "—" or demo_data.get("mother") == "N/A":
            demo_data["mother"] = demo.get("mother") or "—"
        if not demo_data.get("mobile_number") or demo_data.get("mobile_number") == "—" or demo_data.get("mobile_number") == "N/A":
            demo_data["mobile_number"] = demo.get("mobile") or "—"
        if not demo_data.get("address_city") or demo_data.get("address_city") == "—" or demo_data.get("address_city") == "N/A":
            demo_data["address_city"] = demo.get("address") or "—"
            
        data["demographic_data"] = demo_data
        
        # Signature info
        created_by = data.get("created_by")
        emp_details = get_employee_details(created_by)
        data["created_by_name"] = emp_details.get("created_by_name")
        data["created_by_qualification"] = emp_details.get("created_by_qualification")
        data["created_by_designation"] = emp_details.get("created_by_designation") or "Clinical Director / Psychologist"
        data["created_by_signature"] = emp_details.get("created_by_signature", "")
        return data

from .models import ClinicalPsychologyAssessment
class ClinicalPsychologyAssessmentSerializer(SafeJsonFieldsMixin, serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    json_fields = ['behaviour_problems', 'general_temperament', 'behavioral_observation', 'assessments_used']
    class Meta:
        model = ClinicalPsychologyAssessment
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        pk_val = str(getattr(instance, 'pk', None) or getattr(instance, '_id', None) or getattr(instance, 'id', None) or '')
        if pk_val:
            data["id"] = pk_val
            data["_id"] = pk_val

        reg_num = data.get("registrationNumber")
        assessment_date = data.get("assessment_date")
        demo = get_demographics_by_registration(reg_num, ref_date=assessment_date)
        
        for field in ["dob", "father", "mother", "mobile", "address", "age"]:
            if not data.get(field) or data.get(field) == "—" or data.get(field) == "N/A":
                data[field] = demo.get(field, "—")
        
        if not data.get("patientName") or data.get("patientName") == "N/A":
            try:
                from .models import Registration
                patient = Registration.objects.filter(registration_number=reg_num).first()
                if patient:
                    data["patientName"] = patient.name_of_child
            except:
                pass
                
        created_by = data.get("created_by")
        emp_details = get_employee_details(created_by)
        data["created_by_name"] = emp_details.get("created_by_name")
        data["created_by_qualification"] = emp_details.get("created_by_qualification")
        data["created_by_designation"] = emp_details.get("created_by_designation") or "Psychologist"
        data["created_by_signature"] = emp_details.get("created_by_signature", "")
        return data

from .models import OccupationalTherapyAssessment
class OccupationalTherapyAssessmentSerializer(SafeJsonFieldsMixin, serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    json_fields = ['motor_skills', 'handwriting_skills', 'cognitive_concepts', 'visual_perceptual_skills', 'sensory_profile', 'adl_evaluation', 'assessments_used']
    class Meta:
        model = OccupationalTherapyAssessment
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        pk_val = str(getattr(instance, 'pk', None) or getattr(instance, '_id', None) or getattr(instance, 'id', None) or '')
        if pk_val:
            data["id"] = pk_val
            data["_id"] = pk_val

        reg_num = data.get("registrationNumber")
        assessment_date = data.get("assessment_date")
        demo = get_demographics_by_registration(reg_num, ref_date=assessment_date)
        
        for field in ["dob", "father", "mother", "mobile", "address", "age"]:
            if not data.get(field) or data.get(field) == "—" or data.get(field) == "N/A":
                data[field] = demo.get(field, "—")
        
        if not data.get("patientName") or data.get("patientName") == "N/A":
            try:
                from .models import Registration
                patient = Registration.objects.filter(registration_number=reg_num).first()
                if patient:
                    data["patientName"] = patient.name_of_child
            except:
                pass
                
        created_by = data.get("created_by")
        emp_details = get_employee_details(created_by)
        data["created_by_name"] = emp_details.get("created_by_name")
        data["created_by_qualification"] = emp_details.get("created_by_qualification")
        data["created_by_designation"] = emp_details.get("created_by_designation") or "Occupational Therapist"
        data["created_by_signature"] = emp_details.get("created_by_signature", "")
        return data

from .models import SpeechTherapyAssessment
class SpeechTherapyAssessmentSerializer(SafeJsonFieldsMixin, serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    json_fields = ['oral_peripheral_mechanism', 'vegetative_skills', 'speech_parameters', 'communication_profile', 'linguistic_profile', 'assessments_used']
    class Meta:
        model = SpeechTherapyAssessment
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        pk_val = str(getattr(instance, 'pk', None) or getattr(instance, '_id', None) or getattr(instance, 'id', None) or '')
        if pk_val:
            data["id"] = pk_val
            data["_id"] = pk_val

        reg_num = data.get("registrationNumber")
        assessment_date = data.get("assessment_date")
        demo = get_demographics_by_registration(reg_num, ref_date=assessment_date)
        
        for field in ["dob", "father", "mother", "mobile", "address", "age"]:
            if not data.get(field) or data.get(field) == "—" or data.get(field) == "N/A":
                data[field] = demo.get(field, "—")
        
        if not data.get("patientName") or data.get("patientName") == "N/A":
            try:
                from .models import Registration
                patient = Registration.objects.filter(registration_number=reg_num).first()
                if patient:
                    data["patientName"] = patient.name_of_child
            except:
                pass
                
        created_by = data.get("created_by")
        emp_details = get_employee_details(created_by)
        data["created_by_name"] = emp_details.get("created_by_name")
        data["created_by_qualification"] = emp_details.get("created_by_qualification")
        data["created_by_designation"] = emp_details.get("created_by_designation") or "Speech Therapist"
        data["created_by_signature"] = emp_details.get("created_by_signature", "")
        return data

from .models import PhysiotherapyAssessment
class PhysiotherapyAssessmentSerializer(SafeJsonFieldsMixin, serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    json_fields = ['on_observation', 'tone', 'motor_system', 'clonus', 'coordination', 'pattern_and_position', 'limb_length_discrepancy', 'balance', 'sensation', 'assessments_used', 'gross_development', 'reflexes']
    class Meta:
        model = PhysiotherapyAssessment
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        pk_val = str(getattr(instance, 'pk', None) or getattr(instance, '_id', None) or getattr(instance, 'id', None) or '')
        if pk_val:
            data["id"] = pk_val
            data["_id"] = pk_val

        reg_num = data.get("registrationNumber")
        assessment_date = data.get("assessment_date")
        demo = get_demographics_by_registration(reg_num, ref_date=assessment_date)
        
        for field in ["dob", "father", "mother", "mobile", "address", "age"]:
            if not data.get(field) or data.get(field) == "—" or data.get(field) == "N/A":
                data[field] = demo.get(field, "—")
        
        if not data.get("patientName") or data.get("patientName") == "N/A":
            try:
                from .models import Registration
                patient = Registration.objects.filter(registration_number=reg_num).first()
                if patient:
                    data["patientName"] = patient.name_of_child
            except:
                pass
                
        created_by = data.get("created_by")
        emp_details = get_employee_details(created_by)
        data["created_by_name"] = emp_details.get("created_by_name")
        data["created_by_qualification"] = emp_details.get("created_by_qualification")
        data["created_by_designation"] = emp_details.get("created_by_designation") or "Physiotherapist"
        data["created_by_signature"] = emp_details.get("created_by_signature", "")
        return data
        
from .models import AssessmentAnalysis
class AssessmentAnalysisSerializer(SafeJsonFieldsMixin, serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    json_fields = ['preferred_language', 'mapping_therapy', 'session_numbers', 'therapy_methods']
    class Meta:
        model = AssessmentAnalysis
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        reg_num = data.get("registration_number")
        ref_date = data.get("date")
        demo = get_demographics_by_registration(reg_num, ref_date=ref_date)
        
        if not data.get("age") or data.get("age") == "—" or data.get("age") == "N/A":
            data["age"] = demo.get("age", "—")
        if not data.get("patient_name") or data.get("patient_name") == "N/A":
            try:
                from .models import Registration
                patient = Registration.objects.filter(registration_number=reg_num).first()
                if patient:
                    data["patient_name"] = patient.name_of_child
            except:
                pass
                
        created_by = data.get("created_by")
        emp_details = get_employee_details(created_by)
        data["created_by_name"] = emp_details.get("created_by_name")
        data["created_by_qualification"] = emp_details.get("created_by_qualification")
        data["created_by_designation"] = emp_details.get("created_by_designation") or "Clinical Director / Psychologist"
        data["created_by_signature"] = emp_details.get("created_by_signature", "")
        return data

class GoalsAssessmentSerializer(SafeJsonFieldsMixin, serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    patient_details = serializers.SerializerMethodField()
    json_fields = ['goals', 'goalsphoto', 'goalsvideo']

    class Meta:
        model = GoalsAssessment
        fields = '__all__'

    def get_patient_details(self, obj):
        try:
            from .models import Registration
            patient = Registration.objects.filter(registration_number=obj.registration_number).first()
            if patient:
                return RegistrationSerializer(patient).data
        except Exception as e:
            print("Error fetching patient details in GoalsAssessmentSerializer:", e)
        return None

# Mapping to expected name in Views/leave.py
class LeaveFormSerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    class Meta:
        model = leaveform
        fields = '__all__'

class DevelopmentGoalsListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        # Fetch and cache domains, therapies, levels, registrations, and employee details for all objects in the list
        from .models import GoalDomain, TherapyDetails, GoalLevel, Registration
        from bson import ObjectId

        # 1. Fetch all domains
        all_domains = list(GoalDomain.objects.all())
        domains = {d.domain_no: d.name for d in all_domains if d.domain_no}
        domains_by_id = {str(d._id): d.name for d in all_domains if d._id}
        domains_by_name = {d.name: d.name for d in all_domains if d.name}
        
        # 2. Fetch all therapies
        all_therapies = list(TherapyDetails.objects.all())
        therapies = {t.therapy_id: t.therapy_name for t in all_therapies if t.therapy_id}
        therapies_by_id = {str(t._id): t.therapy_name for t in all_therapies if t._id}
        therapies_by_name = {t.therapy_name: t.therapy_name for t in all_therapies if t.therapy_name}
        
        # 3. Fetch all levels
        all_levels = list(GoalLevel.objects.all())
        levels = {l.level_id: l.name for l in all_levels if l.level_id}
        levels_by_id = {str(l._id): l.name for l in all_levels if l._id}
        levels_by_name = {l.name: l.name for l in all_levels if l.name}

        # Save to context
        self.context['domains'] = domains
        self.context['domains_by_id'] = domains_by_id
        self.context['domains_by_name'] = domains_by_name
        self.context['therapies'] = therapies
        self.context['therapies_by_id'] = therapies_by_id
        self.context['therapies_by_name'] = therapies_by_name
        self.context['levels'] = levels
        self.context['levels_by_id'] = levels_by_id
        self.context['levels_by_name'] = levels_by_name

        # Collect registration numbers
        reg_numbers = set()
        for item in data:
            if hasattr(item, 'registration_number') and item.registration_number:
                reg_numbers.add(item.registration_number)
            elif isinstance(item, dict) and item.get('registration_number'):
                reg_numbers.add(item.get('registration_number'))

        patients = {}
        for p in Registration.objects.filter(registration_number__in=list(reg_numbers)):
            patients[p.registration_number] = p
        self.context['patients_map'] = patients

        # Cache employee details
        created_by_ids = set()
        for item in data:
            if hasattr(item, 'created_by') and item.created_by:
                created_by_ids.add(item.created_by)
            elif isinstance(item, dict) and item.get('created_by'):
                created_by_ids.add(item.get('created_by'))
        
        employee_map = {}
        for emp_id in created_by_ids:
            employee_map[emp_id] = get_employee_details(emp_id)
        self.context['employee_map'] = employee_map

        return super().to_representation(data)

class DevelopmentGoalsSerializer(SafeJsonFieldsMixin, serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    goals = serializers.SerializerMethodField()
    registration_details = serializers.SerializerMethodField()
    json_fields = ['development_goals']
    
    class Meta:
        list_serializer_class = DevelopmentGoalsListSerializer
        model = DevelopmentGoals
        fields = [
            'id', 'registration_number', 'date', 'development_goals', 
            'goals', 'registration_details', 'created_by', 'created_date', 
            'lastmodified_by', 'lastmodified_date'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        reg_num = data.get("registration_number")
        ref_date = data.get("date")
        
        patients_map = self.context.get('patients_map')
        demo = None
        if patients_map is not None:
            patient = patients_map.get(reg_num)
            if patient:
                demo = {
                    "dob": "—",
                    "father": "—",
                    "mother": "—",
                    "mobile": "—",
                    "address": "—",
                    "age": "—"
                }
                if patient.dob:
                    if hasattr(patient.dob, 'strftime'):
                        demo["dob"] = patient.dob.strftime('%Y-%m-%d')
                    else:
                        demo["dob"] = str(patient.dob)
                demo["father"] = patient.father_name or "—"
                demo["mother"] = patient.mother_name or "—"
                demo["mobile"] = patient.father_phone_number or patient.mother_phone_number or "—"
                demo["address"] = patient.address or "—"
                
                # Age calculation
                if patient.dob and ref_date:
                    from datetime import datetime
                    try:
                        dob = patient.dob
                        if isinstance(dob, str):
                            dob = datetime.strptime(dob.split('T')[0], '%Y-%m-%d').date()
                        elif isinstance(dob, datetime):
                            dob = dob.date()
                        
                        target_date = ref_date
                        if isinstance(target_date, str):
                            target_date = datetime.strptime(target_date.split('T')[0], '%Y-%m-%d').date()
                        elif isinstance(target_date, datetime):
                            target_date = target_date.date()
                        
                        years = target_date.year - dob.year - ((target_date.month, target_date.day) < (dob.month, dob.day))
                        if target_date.day >= dob.day:
                            months = target_date.month - dob.month
                        else:
                            months = target_date.month - dob.month - 1
                        if months < 0:
                            months += 12
                        
                        parts = []
                        if years > 0:
                            parts.append(f"{years} Years")
                        if months > 0:
                            parts.append(f"{months} Months")
                        demo["age"] = " ".join(parts) if parts else "0 Months"
                    except Exception as e:
                        print("Error calculating age in demo:", e)
                
                if demo["age"] == "—" and patient.age:
                    age_val = patient.age
                    if isinstance(age_val, dict):
                        parts = []
                        year = age_val.get("year") or age_val.get("years")
                        if year is not None:
                            parts.append(f"{year} Years")
                        month = age_val.get("months") or age_val.get("month")
                        if month is not None:
                            parts.append(f"{month} Months")
                        if parts:
                            demo["age"] = " ".join(parts)
        
        if demo is None:
            demo = get_demographics_by_registration(reg_num, ref_date=ref_date)
        
        data["dob"] = demo.get("dob", "—")
        data["father"] = demo.get("father", "—")
        data["mother"] = demo.get("mother", "—")
        data["mobile"] = demo.get("mobile", "—")
        data["address"] = demo.get("address", "—")
        data["age_str"] = demo.get("age", "—")
        
        created_by = data.get("created_by")
        employee_map = self.context.get('employee_map')
        if employee_map is not None and created_by in employee_map:
            emp_details = employee_map[created_by]
        else:
            emp_details = get_employee_details(created_by)
            
        data["created_by_name"] = emp_details.get("created_by_name")
        data["created_by_qualification"] = emp_details.get("created_by_qualification")
        data["created_by_designation"] = emp_details.get("created_by_designation") or ""
        
        if hasattr(instance, '_id') and instance._id:
            data['id'] = str(instance._id)
        elif hasattr(instance, 'pk') and instance.pk:
            data['id'] = str(instance.pk)
            
        data['development_goals'] = data.get('goals', [])
        return data

    def get_goals(self, obj):
        data = obj.development_goals
        if isinstance(data, str):
            try:
                import json
                goals = json.loads(data)
            except:
                goals = []
        elif isinstance(data, list):
            goals = data
        else:
            goals = []

        if isinstance(goals, list) and len(goals) > 0:
            try:
                from .models import GoalDomain, TherapyDetails, GoalLevel
                
                # Fetch and index domains
                domains = self.context.get('domains')
                domains_by_id = self.context.get('domains_by_id')
                domains_by_name = self.context.get('domains_by_name')
                if domains is None or domains_by_id is None or domains_by_name is None:
                    all_domains = list(GoalDomain.objects.all())
                    domains = {d.domain_no: d.name for d in all_domains if d.domain_no}
                    domains_by_id = {str(d._id): d.name for d in all_domains if d._id}
                    domains_by_name = {d.name: d.name for d in all_domains if d.name}
                
                # Fetch and index therapies
                therapies = self.context.get('therapies')
                therapies_by_id = self.context.get('therapies_by_id')
                therapies_by_name = self.context.get('therapies_by_name')
                if therapies is None or therapies_by_id is None or therapies_by_name is None:
                    all_therapies = list(TherapyDetails.objects.all())
                    therapies = {t.therapy_id: t.therapy_name for t in all_therapies if t.therapy_id}
                    therapies_by_id = {str(t._id): t.therapy_name for t in all_therapies if t._id}
                    therapies_by_name = {t.therapy_name: t.therapy_name for t in all_therapies if t.therapy_name}
                
                # Fetch and index levels
                levels = self.context.get('levels')
                levels_by_id = self.context.get('levels_by_id')
                levels_by_name = self.context.get('levels_by_name')
                if levels is None or levels_by_id is None or levels_by_name is None:
                    all_levels = list(GoalLevel.objects.all())
                    levels = {l.level_id: l.name for l in all_levels if l.level_id}
                    levels_by_id = {str(l._id): l.name for l in all_levels if l._id}
                    levels_by_name = {l.name: l.name for l in all_levels if l.name}

                import copy
                goals = copy.deepcopy(goals)

                for g in goals:
                    if isinstance(g, dict):
                        # Map Domain
                        if 'domain' in g:
                            domain_val = g.get('domain')
                            if domain_val in domains:
                                g['domain'] = domains[domain_val]
                            elif domain_val in domains_by_id:
                                g['domain'] = domains_by_id[domain_val]
                            elif domain_val in domains_by_name:
                                g['domain'] = domains_by_name[domain_val]
                                
                        # Map Therapy
                        if 'therapy' in g:
                            therapy_val = g.get('therapy')
                            if therapy_val in therapies:
                                g['therapy'] = therapies[therapy_val]
                            elif therapy_val in therapies_by_id:
                                g['therapy'] = therapies_by_id[therapy_val]
                            elif therapy_val in therapies_by_name:
                                g['therapy'] = therapies_by_name[therapy_val]
                                
                        # Map Level
                        if 'level' in g:
                            level_val = g.get('level')
                            if level_val in levels:
                                g['level'] = levels[level_val]
                            elif level_val in levels_by_id:
                                g['level'] = levels_by_id[level_val]
                            elif level_val in levels_by_name:
                                g['level'] = levels_by_name[level_val]
            except Exception as e:
                print(f"Error mapping goals IDs to names: {e}")

        return goals

    def get_registration_details(self, obj):
        try:
            patients_map = self.context.get('patients_map')
            if patients_map is not None:
                patient = patients_map.get(obj.registration_number)
            else:
                from .models import Registration
                patient = Registration.objects.filter(registration_number=obj.registration_number).first()
                
            if patient:
                data = RegistrationSerializer(patient, context=self.context).data
                if patient.dob and obj.date:
                    from datetime import datetime, date
                    
                    # Robust DOB parsing
                    dob = patient.dob
                    if isinstance(dob, str):
                        try:
                            dob = datetime.strptime(dob.split('T')[0], '%Y-%m-%d').date()
                        except:
                            dob = None
                    
                    # Robust Report Date parsing
                    report_date = obj.date
                    if isinstance(report_date, str):
                        try:
                            report_date = datetime.strptime(report_date.split('T')[0], '%Y-%m-%d').date()
                        except:
                            report_date = date.today()
                    
                    if dob and hasattr(dob, 'year') and hasattr(report_date, 'year'):
                        years = report_date.year - dob.year - ((report_date.month, report_date.day) < (dob.month, dob.day))
                        if report_date.day >= dob.day:
                            months = report_date.month - dob.month
                        else:
                            months = report_date.month - dob.month - 1
                        if months < 0: months += 12
                        
                        data['age'] = {"years": years, "months": months}
                return data
            return None
        except Exception as e:
            import traceback
            print(f"Error calculating age: {e}")
            traceback.print_exc()
            return None

class TherapyDetailsSerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    class Meta:
        model = TherapyDetails
        fields = ['id', 'therapy_name', 'therapy_id', 'color']

class GoalDomainListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        therapies_map = {}
        for t in TherapyDetails.objects.all():
            therapies_map[str(t.pk)] = t.therapy_name
            therapies_map[t.therapy_id] = t.therapy_name
            therapies_map[t.therapy_name] = t.therapy_name
        self.context['therapies_map'] = therapies_map
        return super().to_representation(data)

class GoalDomainSerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    therapy_type_name = serializers.SerializerMethodField()
    class Meta:
        list_serializer_class = GoalDomainListSerializer
        model = GoalDomain
        fields = ['id', 'name', 'therapy_type', 'therapy_type_name', 'domain_no']
    
    def get_therapy_type_name(self, obj):
        val = str(obj.therapy_type or "")
        if not val: return "N/A"
        
        therapies_map = self.context.get('therapies_map')
        if therapies_map is not None:
            return therapies_map.get(val, val)

        try:
            from bson import ObjectId
            if len(val) == 24:
                t = TherapyDetails.objects.get(_id=ObjectId(val))
            else:
                t = TherapyDetails.objects.get(therapy_id=val)
            return t.therapy_name
        except:
            try:
                t = TherapyDetails.objects.get(therapy_name=val)
                return t.therapy_name
            except:
                return val

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'therapy_type' in data: data['therapy_type'] = str(data['therapy_type'])
        return data

class GoalLevelSerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    class Meta:
        model = GoalLevel
        fields = ['id', 'name', 'level_id']

class GoalLibraryListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        therapies_map = {}
        for t in TherapyDetails.objects.all():
            therapies_map[str(t.pk)] = t.therapy_name
            therapies_map[t.therapy_id] = t.therapy_name
            therapies_map[t.therapy_name] = t.therapy_name
            
        domains_map_by_id = {}
        domains_map_by_no = {}
        domains_map_by_name = {}
        for d in GoalDomain.objects.all():
            domains_map_by_id[str(d.pk)] = d
            domains_map_by_no[d.domain_no] = d
            domains_map_by_name[d.name] = d

        levels_map = {}
        for l in GoalLevel.objects.all():
            levels_map[str(l.pk)] = l.name
            levels_map[l.level_id] = l.name
            levels_map[l.name] = l.name

        self.context['therapies_map'] = therapies_map
        self.context['domains_map_by_id'] = domains_map_by_id
        self.context['domains_map_by_no'] = domains_map_by_no
        self.context['domains_map_by_name'] = domains_map_by_name
        self.context['levels_map'] = levels_map

        return super().to_representation(data)

class GoalLibrarySerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    therapy_type_name = serializers.SerializerMethodField()
    domain_name = serializers.SerializerMethodField()
    domain_no = serializers.SerializerMethodField()
    level_name = serializers.SerializerMethodField()
    
    class Meta:
        list_serializer_class = GoalLibraryListSerializer
        model = GoalLibrary
        fields = ['id', 'goal_name', 'goal_no', 'domain', 'domain_name', 'domain_no', 'therapy_type', 'therapy_type_name', 'level', 'level_name', 'is_custom']

    def get_therapy_type_name(self, obj):
        val = str(obj.therapy_type or "")
        if not val: return "N/A"
        
        therapies_map = self.context.get('therapies_map')
        if therapies_map is not None:
            return therapies_map.get(val, val)

        try:
            t = TherapyDetails.objects.get(therapy_id=val)
            return t.therapy_name
        except: pass

        if len(val) == 24:
            try:
                from bson import ObjectId
                t = TherapyDetails.objects.get(_id=ObjectId(val))
                return t.therapy_name
            except: pass
            
        try:
            t = TherapyDetails.objects.get(therapy_name=val)
            return t.therapy_name
        except: pass

        return val

    def get_domain_name(self, obj):
        val = str(obj.domain or "")
        if not val: return "N/A"
        
        domains_map_by_id = self.context.get('domains_map_by_id')
        domains_map_by_no = self.context.get('domains_map_by_no')
        domains_map_by_name = self.context.get('domains_map_by_name')
        
        if domains_map_by_id is not None and domains_map_by_no is not None and domains_map_by_name is not None:
            d = domains_map_by_id.get(val) or domains_map_by_no.get(val) or domains_map_by_name.get(val)
            if d: return d.name
            return val

        try:
            d = GoalDomain.objects.get(domain_no=val)
            return d.name
        except: pass

        if len(val) == 24:
            try:
                from bson import ObjectId
                d = GoalDomain.objects.get(_id=ObjectId(val))
                return d.name
            except: pass

        try:
            d = GoalDomain.objects.get(name=val)
            return d.name
        except: pass

        return val

    def get_domain_no(self, obj):
        val = str(obj.domain or "")
        if not val: return "N/A"

        domains_map_by_id = self.context.get('domains_map_by_id')
        domains_map_by_no = self.context.get('domains_map_by_no')
        domains_map_by_name = self.context.get('domains_map_by_name')
        
        if domains_map_by_id is not None and domains_map_by_no is not None and domains_map_by_name is not None:
            d = domains_map_by_id.get(val) or domains_map_by_no.get(val) or domains_map_by_name.get(val)
            if d: return d.domain_no
            return val

        try:
            d = GoalDomain.objects.get(domain_no=val)
            return d.domain_no
        except: pass

        if len(val) == 24:
            try:
                from bson import ObjectId
                d = GoalDomain.objects.get(_id=ObjectId(val))
                return d.domain_no
            except: pass

        try:
            d = GoalDomain.objects.get(name=val)
            return d.domain_no
        except: pass

        return val

    def get_level_name(self, obj):
        val = str(obj.level or "")
        if not val: return "-"

        levels_map = self.context.get('levels_map')
        if levels_map is not None:
            return levels_map.get(val, val)

        try:
            l = GoalLevel.objects.get(level_id=val)
            return l.name
        except: pass

        if len(val) == 24:
            try:
                from bson import ObjectId
                l = GoalLevel.objects.get(_id=ObjectId(val))
                return l.name
            except: pass

        try:
            l = GoalLevel.objects.get(name=val)
            return l.name
        except: pass

        return val

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'therapy_type' in data: data['therapy_type'] = str(data['therapy_type'])
        if 'domain' in data: data['domain'] = str(data['domain'])
        if 'level' in data: data['level'] = str(data['level'])
        return data


class ActivityLibraryListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        therapies_map = {}
        for t in TherapyDetails.objects.all():
            therapies_map[str(t.pk)] = t.therapy_name
            therapies_map[t.therapy_id] = t.therapy_name
            therapies_map[t.therapy_name] = t.therapy_name
            
        domains_map_by_id = {}
        domains_map_by_no = {}
        domains_map_by_name = {}
        for d in GoalDomain.objects.all():
            domains_map_by_id[str(d.pk)] = d
            domains_map_by_no[d.domain_no] = d
            domains_map_by_name[d.name] = d

        self.context['therapies_map'] = therapies_map
        self.context['domains_map_by_id'] = domains_map_by_id
        self.context['domains_map_by_no'] = domains_map_by_no
        self.context['domains_map_by_name'] = domains_map_by_name

        return super().to_representation(data)


class ActivityLibrarySerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    therapy_type_name = serializers.SerializerMethodField()
    domain_name = serializers.SerializerMethodField()
    domain_no = serializers.SerializerMethodField()
    
    class Meta:
        list_serializer_class = ActivityLibraryListSerializer
        model = ActivityLibrary
        fields = ['id', 'task_name', 'task_id', 'domain', 'domain_name', 'domain_no', 'therapy_type', 'therapy_type_name', 'is_custom']

    def get_therapy_type_name(self, obj):
        val = str(obj.therapy_type or "")
        if not val: return "N/A"
        
        therapies_map = self.context.get('therapies_map')
        if therapies_map is not None:
            return therapies_map.get(val, val)

        try:
            t = TherapyDetails.objects.get(therapy_id=val)
            return t.therapy_name
        except: pass

        if len(val) == 24:
            try:
                from bson import ObjectId
                t = TherapyDetails.objects.get(_id=ObjectId(val))
                return t.therapy_name
            except: pass
            
        try:
            t = TherapyDetails.objects.get(therapy_name=val)
            return t.therapy_name
        except: pass

        return val

    def get_domain_name(self, obj):
        val = str(obj.domain or "")
        if not val: return "N/A"
        
        domains_map_by_id = self.context.get('domains_map_by_id')
        domains_map_by_no = self.context.get('domains_map_by_no')
        domains_map_by_name = self.context.get('domains_map_by_name')
        
        if domains_map_by_id is not None and domains_map_by_no is not None and domains_map_by_name is not None:
            d = domains_map_by_id.get(val) or domains_map_by_no.get(val) or domains_map_by_name.get(val)
            if d: return d.name
            return val

        try:
            d = GoalDomain.objects.get(domain_no=val)
            return d.name
        except: pass

        if len(val) == 24:
            try:
                from bson import ObjectId
                d = GoalDomain.objects.get(_id=ObjectId(val))
                return d.name
            except: pass

        try:
            d = GoalDomain.objects.get(name=val)
            return d.name
        except: pass

        return val

    def get_domain_no(self, obj):
        val = str(obj.domain or "")
        if not val: return "N/A"

        domains_map_by_id = self.context.get('domains_map_by_id')
        domains_map_by_no = self.context.get('domains_map_by_no')
        domains_map_by_name = self.context.get('domains_map_by_name')
        
        if domains_map_by_id is not None and domains_map_by_no is not None and domains_map_by_name is not None:
            d = domains_map_by_id.get(val) or domains_map_by_no.get(val) or domains_map_by_name.get(val)
            if d: return d.domain_no
            return val

        try:
            d = GoalDomain.objects.get(domain_no=val)
            return d.domain_no
        except: pass

        if len(val) == 24:
            try:
                from bson import ObjectId
                d = GoalDomain.objects.get(_id=ObjectId(val))
                return d.domain_no
            except: pass

        try:
            d = GoalDomain.objects.get(name=val)
            return d.domain_no
        except: pass

        return val

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'therapy_type' in data: data['therapy_type'] = str(data['therapy_type'])
        if 'domain' in data: data['domain'] = str(data['domain'])
        return data


class DailyTimeSlotSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = DailyTimeSlot
        fields = '__all__'


class PatientSessionAttendanceSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = PatientSessionAttendance
        fields = '__all__'
        read_only_fields = ['id', 'session_id']

class AppointmentScheduleSerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    class Meta:
        model = AppointmentSchedule
        fields = '__all__'

from .models import EnquiryForm

class EnquiryFormSerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)

    class Meta:
        model = EnquiryForm
        fields = '__all__'

    def validate_age(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError("Age must be a positive number.")
        return value

    def validate_mobile_number(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError("Mobile number must contain digits only.")
        return value  

class BehavioralObservationOptionSerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    class Meta:
        model = BehavioralObservationOption
        fields = ['id', 'name']


from rest_framework import serializers
from .models import CrossConsultationPlan, CrossTherapyRecommendation, RECOMMENDATION_ROLES


class CrossConsultationPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrossConsultationPlan
        fields = [
            "id",
            "registration_number",
            "patient_name",
            "age_sex",
            "entries",
            "created_by",
            "created_date",
            "lastmodified_by",
            "lastmodified_date",
        ]
        read_only_fields = ["created_by", "created_date", "lastmodified_by", "lastmodified_date"]


class CrossTherapyRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrossTherapyRecommendation
        fields = [
            "id",
            "registration_number",
            "patient_name",
            "age_sex",
            "recommendations",
            "created_by",
            "created_date",
            "lastmodified_by",
            "lastmodified_date",
        ]
        read_only_fields = ["created_by", "created_date", "lastmodified_by", "lastmodified_date"]

    def validate_recommendations(self, value):
        for row in value:
            role = row.get("recommendation_by")
            if role and role not in RECOMMENDATION_ROLES:
                raise serializers.ValidationError(
                    f"'{role}' is not a valid recommendation_by role. "
                    f"Expected one of: {', '.join(RECOMMENDATION_ROLES)}"
                )
        return value
    


from rest_framework import serializers
from .models import CrossTherapyRecommendation

class CrossTherapyRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrossTherapyRecommendation
        fields = '__all__'