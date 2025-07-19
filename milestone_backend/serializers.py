from rest_framework import serializers
from .models import Registration,PatientAssessment
from bson import ObjectId
from .models import ReferralDoctor
from rest_framework import serializers
from .models import PediatricAssessment
from rest_framework import serializers
from .models import TherapyBilling
from bson import ObjectId  # Import for handling MongoDB ObjectId
from rest_framework import serializers
from .models import OthersBilling
from bson import ObjectId  # Import for handling MongoDB ObjectId


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


class TherapyBillingSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False)
    id = serializers.SerializerMethodField()  # Convert ObjectId to string

    def get_id(self, obj):
        return str(obj.id) if isinstance(obj.id, ObjectId) else obj.id

    class Meta:
        model = TherapyBilling
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
    # Handle ObjectId serialization (if you're using djongo/MongoDB)
    id = serializers.CharField(read_only=True)
    
    class Meta:
        model = ReferralDoctor
        fields = "__all__"
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
