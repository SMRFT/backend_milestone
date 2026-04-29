from rest_framework import serializers
from .models import (
    Registration, PatientAssessment, EmployeeRegistration, DevelopmentalTask, 
    PediatricAssessment, SkillTestResult, TherapyBilling, OthersBilling, 
    MCHATResponse, ReferralDoctor, ChildLanguageAssessment, DevelopmentalScreeningTask, 
    CBCL, ConsultingDoctor, PatientAttendance, HistoryRecordingSheet, 
    ClinicalPsychologyAssessment, OccupationalTherapyAssessment, SpeechTherapyAssessment, 
    PhysiotherapyAssessment, AssessmentAnalysis, GoalsAssessment, leaveform, 
    DevelopmentGoals, TherapyDetails, GoalDomain, GoalLevel, GoalLibrary
)
from djongo.models import ObjectIdField

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

class GoalsAssessmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    class Meta:
        model = GoalsAssessment
        fields = '__all__'

# Mapping to expected name in Views/leave.py
class LeaveFormSerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    class Meta:
        model = leaveform
        fields = '__all__'

class DevelopmentGoalsSerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    goals = serializers.SerializerMethodField()
    registration_details = serializers.SerializerMethodField()
    
    class Meta:
        model = DevelopmentGoals
        fields = [
            'id', 'registration_number', 'date', 'development_goals', 
            'goals', 'registration_details', 'created_by', 'created_date', 
            'lastmodified_by', 'lastmodified_date'
        ]

    def get_goals(self, obj):
        data = obj.development_goals
        if isinstance(data, str):
            try:
                import json
                return json.loads(data)
            except:
                return []
        if isinstance(data, list):
            return data
        return []

    def get_registration_details(self, obj):
        try:
            patient = Registration.objects.filter(registration_number=obj.registration_number).first()
            if patient:
                data = RegistrationSerializer(patient).data
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Ensure 'id' is always present as a string for the frontend
        if hasattr(instance, '_id') and instance._id:
            data['id'] = str(instance._id)
        elif hasattr(instance, 'pk') and instance.pk:
            data['id'] = str(instance.pk)
            
        data['development_goals'] = data.get('goals', [])
        return data

class TherapyDetailsSerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    class Meta:
        model = TherapyDetails
        fields = ['id', 'therapy_name']

class GoalDomainSerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    therapy_type_name = serializers.SerializerMethodField()
    class Meta:
        model = GoalDomain
        fields = ['id', 'name', 'therapy_type', 'therapy_type_name', 'domain_no']
    
    def get_therapy_type_name(self, obj):
        try:
            from bson import ObjectId
            # Use TherapyDetails instead of GoalTherapyType
            t = TherapyDetails.objects.get(_id=ObjectId(obj.therapy_type))
            return t.therapy_name
        except: return "N/A"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Force these to be strings
        if 'therapy_type' in data: data['therapy_type'] = str(data['therapy_type'])
        return data

class GoalLevelSerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    class Meta:
        model = GoalLevel
        fields = ['id', 'name']

class GoalLibrarySerializer(serializers.ModelSerializer):
    id = ObjectIdField(source='_id', read_only=True)
    therapy_type_name = serializers.SerializerMethodField()
    domain_name = serializers.SerializerMethodField()
    domain_no = serializers.SerializerMethodField()
    level_name = serializers.SerializerMethodField()
    
    class Meta:
        model = GoalLibrary
        fields = ['id', 'goal_name', 'goal_no', 'domain', 'domain_name', 'domain_no', 'therapy_type', 'therapy_type_name', 'level', 'level_name']

    def get_therapy_type_name(self, obj):
        val = str(obj.therapy_type or "")
        if not val: return "N/A"
        if len(val) != 24: return val
        try:
            from bson import ObjectId
            t = TherapyDetails.objects.get(_id=ObjectId(val))
            return t.therapy_name
        except: return val

    def get_domain_name(self, obj):
        val = str(obj.domain or "")
        if not val: return "N/A"
        if len(val) != 24: return val
        try:
            from bson import ObjectId
            d = GoalDomain.objects.get(_id=ObjectId(val))
            return d.name
        except: return val

    def get_domain_no(self, obj):
        val = str(obj.domain or "")
        if not val: return "N/A"
        if len(val) != 24: return val
        try:
            from bson import ObjectId
            d = GoalDomain.objects.get(_id=ObjectId(val))
            return d.domain_no
        except: return val

    def get_level_name(self, obj):
        val = str(obj.level or "")
        if not val: return "-"
        if len(val) != 24: return val
        try:
            from bson import ObjectId
            l = GoalLevel.objects.get(_id=ObjectId(val))
            return l.name
        except: return val

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'therapy_type' in data: data['therapy_type'] = str(data['therapy_type'])
        if 'domain' in data: data['domain'] = str(data['domain'])
        if 'level' in data: data['level'] = str(data['level'])
        return data