from rest_framework import serializers
from .models import Registration,PatientAssessment
from bson import ObjectId
from .models import ReferralDoctor
from .models import ConsultingDoctor
from rest_framework import serializers
from .models import PediatricAssessment
from rest_framework import serializers
from .models import TherapyBilling
from bson import ObjectId  # Import for handling MongoDB ObjectId
from rest_framework import serializers
from .models import OthersBilling
import os
from pymongo import DESCENDING, MongoClient
from datetime import datetime ,timedelta ,date
import json
from bson import ObjectId  # Import for handling MongoDB ObjectId
from bson.decimal128 import Decimal128
from datetime import datetime, date

class ObjectIdField(serializers.Field):
    def to_representation(self, value):
        return str(value)
    def to_internal_value(self, data):
        return ObjectId(data)
    
class RegistrationSerializer(serializers.ModelSerializer):
    # Handle ObjectId serialization
    id = serializers.CharField(read_only=True)  # Override the ObjectId field
    
    class Meta:
        model = Registration
        fields = '__all__'
        # Make audit fields read-only since we'll set them programmatically
        read_only_fields = ['id', 'created_by', 'created_date', 'lastmodified_date']
    def to_representation(self, instance):
        """Custom serialization to handle ObjectId"""
        data = super().to_representation(instance)
        
        # Convert ObjectId to string if present
        if 'id' in data and data['id'] is not None:
            data['id'] = str(data['id'])
            
        return data
    
    def create(self, validated_data):
        # Get the employee_id from the context (passed from the view)
        employee_id = self.context.get('employee_id')
        
        # Set the created_by field
        if employee_id:
            validated_data['created_by'] = employee_id
            
        return super().create(validated_data)

from rest_framework import serializers
from .models import EmployeeRegistration

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
    
    def to_representation(self, instance):
        """Custom serialization to handle ObjectId"""
        data = super().to_representation(instance)
        
        # Convert ObjectId to string if present
        if 'id' in data and data['id'] is not None:
            data['id'] = str(data['id'])
            
        return data
    
    def create(self, validated_data):
        # Get the employee_id from the context (passed from the view)
        employee_id = self.context.get('employee_id')
        
        # Set the created_by field
        if employee_id:
            validated_data['created_by'] = employee_id
            
        return super().create(validated_data)

class PediatricAssessmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
       
        model = PediatricAssessment
        fields = '__all__'

from bson import ObjectId
from decimal import Decimal

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
    
class OthersBillingSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False)
    id = serializers.SerializerMethodField()  # Convert ObjectId to string

    def get_id(self, obj):
        return str(obj.id) if isinstance(obj.id, ObjectId) else obj.id

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

class MCHATResponseSerializer(serializers.ModelSerializer):
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

class ChildLanguageAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildLanguageAssessment
        fields = '__all__'

# serializers.py

from rest_framework import serializers
from .models import DevelopmentalScreeningTask

class DevelopmentalScreeningTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = DevelopmentalScreeningTask
        fields = '__all__'

from rest_framework import serializers
from .models import CBCL
from bson import ObjectId  # Import to handle MongoDB ObjectId

class CBCLSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()  # Add this field

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
from .models import PatientAttendance

class PatientAttendanceSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = PatientAttendance
        fields =  '__all__' # ['id', 'registration_number', 'date', 'session', 'therapy_charge']

from rest_framework import serializers
from .models import HistoryRecordingSheet

class HistoryRecordingSheetSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = HistoryRecordingSheet
        fields =  '__all__' 

from .models import ClinicalPsychologyAssessment
class ClinicalPsychologyAssessmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = ClinicalPsychologyAssessment
        fields = "__all__"

from .models import OccupationalTherapyAssessment
class OccupationalTherapyAssessmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = OccupationalTherapyAssessment
        fields = "__all__"

from .models import SpeechTherapyAssessment
class SpeechTherapyAssessmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = SpeechTherapyAssessment
        fields = "__all__"

from .models import PhysiotherapyAssessment
class PhysiotherapyAssessmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = PhysiotherapyAssessment
        fields = "__all__"
        
from .models import AssessmentAnalysis
class AssessmentAnalysisSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = AssessmentAnalysis
        fields = "__all__"

from rest_framework import serializers
from .models import GoalsAssessment

from .models import Registration  # make sure imported

import ast
import json

import re

def parse_python_string(val):
    """
    Very robust helper to convert stringified Python objects (like OrderedDict)
    back into proper Python dictionaries or lists.
    """
    if not isinstance(val, str):
        return val
    
    val = val.strip()
    if not val:
        return val

    # 1. If it's explicitly a string beginning with OrderedDict
    if "OrderedDict" in val:
        try:
            # Handle potential nesting: OrderedDict([('url', '...'), ('id', '...')])
            # A simple way is to find the first '(' and last ')'
            start = val.find('(')
            end = val.rfind(')')
            if start != -1 and end != -1:
                inner = val[start+1:end]
                # Try literal_eval on the inner list of tuples
                parsed = ast.literal_eval(inner)
                if isinstance(parsed, list):
                    return dict(parsed)
        except Exception:
            pass

    # 2. Try the regex extraction if we just want the ID from OrderedDict([('url', '...'), ('id', '69956...')])
    # This is a bit of a hack but very effective for this specific issue
    id_match = re.search(r"'id',\s*'([a-f0-9]{24})'", val)
    if id_match:
        return id_match.group(1)

    # 3. Fallback to standard literal_eval for lists/dicts as strings
    try:
        return ast.literal_eval(val)
    except Exception:
        # Final fallback: standard JSON or the string itself
        try:
            return json.loads(val)
        except Exception:
            return val

class GoalsAssessmentSerializer(serializers.ModelSerializer):
    patient_details = serializers.SerializerMethodField()
    id = serializers.CharField(source="_id", read_only=True)

    class Meta:
        model = GoalsAssessment
        fields = "__all__"
        read_only_fields = ("_id",)

    def to_representation(self, instance):
        """Custom serialization to handle file serving URLs"""
        data = super().to_representation(instance)
        
        # Helper to ensure we have a clean list of objects/ids
        def ensure_clean_list(val):
            if not val: return []
            
            # 1. Ensure it's a list first
            raw_list = val
            if isinstance(val, str):
                parsed = parse_python_string(val)
                raw_list = parsed if isinstance(parsed, list) else [parsed]
            
            if not isinstance(raw_list, list):
                raw_list = [raw_list]
                
            # 2. Clean each element in the list
            cleaned_list = []
            for item in raw_list:
                if not item: continue
                cleaned_item = parse_python_string(item)
                cleaned_list.append(cleaned_item)
            return cleaned_list

        # Transform goalsphoto from [id1, ...] to [{"file": id1, "url": "..."}, ...]
        if 'goalsphoto' in data:
            photos = ensure_clean_list(data['goalsphoto'])
            formatted_photos = []
            for p in photos:
                # Extract file_id: could be string ID, or dict with file/id key
                if isinstance(p, dict):
                    file_id = p.get('file') or p.get('id') or p.get('_id')
                else:
                    file_id = str(p)
                
                if file_id:
                    # Always generate a local-style URL, don't use external ones
                    url = f"/goals/file/{file_id}/"
                    formatted_photos.append({"file": file_id, "url": url})
            data['goalsphoto'] = formatted_photos

        # Transform goalsvideo from [id1, ...] to [{"file": id1, "url": "..."}, ...]
        if 'goalsvideo' in data:
            videos = ensure_clean_list(data['goalsvideo'])
            formatted_videos = []
            for v in videos:
                if isinstance(v, dict):
                    file_id = v.get('file') or v.get('id') or v.get('_id')
                else:
                    file_id = str(v)
                
                if file_id:
                    url = f"/goals/file/{file_id}/"
                    formatted_videos.append({"file": file_id, "url": url})
            data['goalsvideo'] = formatted_videos

        return data

    def get_patient_details(self, obj):
        try:
            patient = Registration.objects.get(
                registration_number=obj.registration_number
            )
            return RegistrationSerializer(patient).data
        except Registration.DoesNotExist:
            return None

    def validate(self, data):
        # ✅ ONLY validate duplicates during CREATE
        if self.instance:
            return data   # skip validation for updates

        registration_number = data.get("registration_number")
        date = data.get("date")

        if GoalsAssessment.objects.filter(
            registration_number=registration_number,
            date=date
        ).exists():
            raise serializers.ValidationError(
                "Goal already exists for this registration number on this date. "
                "Please use update endpoint."
            )

        return data

from rest_framework import serializers
from .models import leaveform

class LeaveFormSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    
    class Meta:
        model = leaveform
        fields = '__all__'