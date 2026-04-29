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
        return data

class RegistrationSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = Registration
        fields = '__all__'

class PatientAssessmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)    
    class Meta:
        model = PatientAssessment
        fields = '__all__'

class EmployeeRegistrationSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = EmployeeRegistration
        fields = '__all__'

class DevelopmentalTaskSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = DevelopmentalTask
        fields = '__all__'

class PediatricAssessmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = PediatricAssessment
        fields = '__all__'

class SkillTestResultSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = SkillTestResult
        fields = '__all__'

class TherapyBillingSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = TherapyBilling
        fields = '__all__'

class OthersBillingSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = OthersBilling
        fields = '__all__'

class MCHATResponseSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = MCHATResponse
        fields = '__all__'

class ReferralDoctorSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = ReferralDoctor
        fields = '__all__'

class ChildLanguageAssessmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)

    class Meta:
        model = ChildLanguageAssessment
        fields = '__all__'

class DevelopmentalScreeningTaskSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = DevelopmentalScreeningTask
        fields = '__all__'

class CBCLSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = CBCL
        fields = '__all__'

class ConsultingDoctorSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = ConsultingDoctor
        fields = '__all__'

class PatientAttendanceSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = PatientAttendance
        fields = '__all__'

class HistoryRecordingSheetSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = HistoryRecordingSheet
        fields = '__all__'

class ClinicalPsychologyAssessmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = ClinicalPsychologyAssessment
        fields = '__all__'

class OccupationalTherapyAssessmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = OccupationalTherapyAssessment
        fields = '__all__'

class SpeechTherapyAssessmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = SpeechTherapyAssessment
        fields = '__all__'

class PhysiotherapyAssessmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = PhysiotherapyAssessment
        fields = '__all__'

class AssessmentAnalysisSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = AssessmentAnalysis
        fields = '__all__'

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