from rest_framework import serializers
from .models import Registration,PatientAssessment,Login
from bson import ObjectId

class ObjectIdField(serializers.Field):
    def to_representation(self, value):
        return str(value)
    def to_internal_value(self, data):
        return ObjectId(data)
    
class RegistrationSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = Registration
        fields = '__all__'

from rest_framework import serializers
from .models import EmployeeRegistration

class EmployeeRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeRegistration
        fields = '__all__'


class PatientAssessmentSerializer(serializers.ModelSerializer):
 # Nested serializer for assessments
    id = ObjectIdField(read_only=True)
    class Meta:
        model = PatientAssessment
        fields = '__all__'



class LoginSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = Login
        fields = '__all__'





from rest_framework import serializers
from .models import PediatricAssessment

class PediatricAssessmentSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
       
        model = PediatricAssessment
        fields = '__all__'


from rest_framework import serializers
from .models import TherapyBilling
from bson import ObjectId  # Import for handling MongoDB ObjectId

class TherapyBillingSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False)  # Include time in format
    id = serializers.SerializerMethodField()  # Convert ObjectId to string

    def get_id(self, obj):
        return str(obj.id) if isinstance(obj.id, ObjectId) else obj.id  # Convert ObjectId to string

    class Meta:
        model = TherapyBilling
        fields = "__all__"


from rest_framework import serializers
from .models import MCHATResponse

class MCHATResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCHATResponse
        fields = ['registration_number','patient_name', 'age', 'sex', 'question', 'score','riskLevel']

from rest_framework import serializers
from .models import ReferralDoctor

class ReferralDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralDoctor
        fields = "__all__"




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
