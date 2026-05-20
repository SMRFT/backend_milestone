import json
from ..serializers import RegistrationSerializer
from ..models import Registration, PatientAssessment
from rest_framework.response import Response
from datetime import datetime ,timedelta ,date
from rest_framework.decorators import api_view , permission_classes
from rest_framework import status
from ..models import PatientAssessment
from ..serializers import PatientAssessmentSerializer,HistoryRecordingSheetSerializer
from django.db.models import Max
from django.http import JsonResponse
from ..models import Registration
from pyauth.auth import HasRolePermission
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

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
from dateutil.relativedelta import relativedelta
from django.shortcuts import get_object_or_404
from pymongo import DESCENDING, MongoClient
import gridfs
import os
import certifi
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()  # Load from .env if present

env_type = os.environ.get("ENV_CLASSIFICATION", "local")

mongo_uri = os.environ.get("GLOBAL_DB_HOST")
db_name = os.environ.get("MILESTONE_DB_NAME", "Milestone")

if env_type in ["test", "prod"]:
    client = MongoClient(mongo_uri)
else:
    client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())

@api_view(['POST'])
@permission_classes([HasRolePermission])
def create_registration(request):
    # Extract employee ID from request
    employee_id = request.data.get('auth-user-id')
    
    # Pass employee_id through context
    serializer = RegistrationSerializer(data=request.data, context={'employee_id': employee_id})
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)



@api_view(['PATCH'])
@permission_classes([HasRolePermission])
def update_registration(request, registration_number):
    """
    Update registration with automatic audit field population using registration_number
    """
    try:
        # MongoDB connection setup
        mongo_uri = os.environ.get("GLOBAL_DB_HOST")
        db_name = os.environ.get("MILESTONE_DB_NAME", "Milestone")
        collection_name = "milestone_backend_registration"  # Assuming this is the collection name
        
        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        db = client[db_name]
        collection = db[collection_name]
        
        # Find the document by registration_number
        registration_doc = collection.find_one({"registration_number": registration_number})
        
        if not registration_doc:
            return Response(
                {'error': 'Registration not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Extract employee ID from request
        employee_id = request.data.get('auth-user-id')
        
        # Prepare update data
        update_data = {}
        
        # Add fields from request data (excluding system fields)
        excluded_fields = ['_id', 'created_at', 'lastmodified_date', 'lastmodified_by', 'registration_number']
        for key, value in request.data.items():
            if key not in excluded_fields:
                if key in ['age', 'reason_for_visit', 'source_of_referral']:
                    update_data[key] = safe_parse_json(value)
                else:
                    update_data[key] = value
        
        # Add audit fields
        update_data['lastmodified_date'] = datetime.now()
        if employee_id:
            update_data['lastmodified_by'] = employee_id
        
        # Perform the update
        result = collection.update_one(
            {"registration_number": registration_number},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            # Fetch the updated document
            updated_doc = collection.find_one({"registration_number": registration_number})
            
            # Convert ObjectId to string for JSON serialization
            if '_id' in updated_doc:
                updated_doc['_id'] = str(updated_doc['_id'])
            
            # Convert datetime objects to ISO format strings
            for key, value in updated_doc.items():
                if isinstance(value, datetime):
                    updated_doc[key] = value.isoformat()
            
            return Response(updated_doc, status=status.HTTP_200_OK)
        else:
            return Response(
                {'message': 'No changes were made'}, 
                status=status.HTTP_200_OK
            )
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        # Always close the MongoDB connection
        if 'client' in locals():
            client.close()

from ..models import Registration, PatientAssessment, PatientAttendance
from ..serializers import RegistrationSerializer
import json

@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_all_patients(request):
    # Get today's date
    today = datetime.utcnow().date()
    # Get all patients from the Registration model
    patients = Registration.objects.all()
    # Get all patient assessments
    patient_assessments = PatientAssessment.objects.all()
    # Filter assessments for today in Python
    assessed_patients_today = {
        assessment.registration_number
        for assessment in patient_assessments
        if assessment.date.date() == today
    }
           # Create a list of patient data without the 'disabled' field
    patient_data = []
    for patient in patients:
        # Serialize patient data using RegistrationSerializer
        patient_info = RegistrationSerializer(patient).data
        # Add patient data to the list without the 'disabled' field
        patient_data.append(patient_info)
    # Return the patient data in the response
    return Response(patient_data)

@api_view(['GET'])
# @permission_classes([HasRolePermission])
def get_all_patients_filterless(request):
    # Get all patients from the Registration model
    patients = Registration.objects.all()

    # Serialize all patients
    patient_data = RegistrationSerializer(patients, many=True).data

    # Return the patient data in the response
    return Response(patient_data)

@api_view(['GET'])
@permission_classes([HasRolePermission])    
def get_all_assessments(request):
    db = client[db_name]          
    fs = gridfs.GridFS(db)       
    try:
        # Fetch all documents from the milestone_backend_Billing collection
        billing_data = list(db['milestone_backend_Billing'].find({}, {'_id': 0}))

        # Initialize the response data with empty lists
        response_data = {
            "psychological_assessments": [],
            "speech_assessments": [],
            "ot_assessments": [],
            "physio_therapy_assessments": [],
            "drs_consulting": []
        }

        # Loop through each document and collect assessments
        for document in billing_data:
            response_data["psychological_assessments"].extend(document.get("psychological_assessments", []))
            response_data["speech_assessments"].extend(document.get("speech_assessments", []))
            response_data["ot_assessments"].extend(document.get("ot_assessments", []))
            response_data["physio_therapy_assessments"].extend(document.get("physio_therapy_assessments", []))
            response_data["drs_consulting"].extend(document.get("drs_consulting", []))

        # Return the combined data as JSON
        return JsonResponse(response_data, safe=False, json_dumps_params={'indent': 2})

    except Exception as e:      
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['POST'])
@permission_classes([HasRolePermission])
def save_assessments(request):
    if request.method == 'POST':
        # Extract employee ID from request
        employee_id = request.data.get('auth-user-id')
        
        # Pass employee_id through context
        serializer = PatientAssessmentSerializer(data=request.data, context={'employee_id': employee_id})
        
        if serializer.is_valid():
            serializer.save()  # Save the new patient assessment to the database
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_assessments(request):
    # Retrieve all patient assessments
    assessments = PatientAssessment.objects.all()
    
    # Serialize all the assessments
    serializer = PatientAssessmentSerializer(assessments, many=True)
    
    # Return the serialized data as a response
    return Response(serializer.data, status=status.HTTP_200_OK)

# To get the next registration number
@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_next_registration_number(request):
    last_reg = Registration.objects.all().order_by('id').last()
    if last_reg:
        last_reg_no = last_reg.registration_number.split('/')[1]
        new_reg_no = int(last_reg_no) + 1
    else:
        new_reg_no = 1  # Start with 1 if no registrations exist
    current_year = datetime.datetime.now().year
    next_registration_number = f'MDC/{new_reg_no:03}/{current_year}'
    
    return Response({'next_registration_number': next_registration_number})@api_view(['GET'])

@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_latest_registration_number(request):
    # Fetch the latest registration number from the database
    latest_registration = Registration.objects.aggregate(Max('registration_number'))

    # Get the current year
    current_year = datetime.now().year

    # If there's a registration number, increment it, otherwise start with MDC/001/current_year
    if latest_registration['registration_number__max']:
        # Extract the numeric part and increment it
        reg_no = latest_registration['registration_number__max'].split('/')[1]
        current_id = int(reg_no)
        new_registration_number = f"MDC/{str(current_id + 1).zfill(3)}/{current_year}"
    else:
        # Start the numbering with MDC/001/current_year if no previous registration exists
        new_registration_number = f"MDC/001/{current_year}"

    # Return the registration number in JSON format using DRF's Response
    return Response({"registration_number": new_registration_number}, status=status.HTTP_200_OK)

def get_patient_by_registration(request, prefix, id, year):
    try:
        registration_number = f"{prefix}/{id}/{year}"
        patient = Registration.objects.get(registration_number=registration_number)
        return JsonResponse({
            "name_of_child": patient.name_of_child,
            "age": safe_parse_json(patient.age),
            "sex": patient.sex,
            # other fields...
        })
    except Registration.DoesNotExist:
        return JsonResponse({"error": "Patient not found"}, status=404)
    
@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_referrals(request):
    try:
        # Get the date range from query parameters
        from_date_str = request.GET.get('fromDate', '')
        to_date_str = request.GET.get('toDate', '')
        
        # Convert strings to datetime objects
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d') if from_date_str else None
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d') if to_date_str else None
        
        # Filter registrations based on the date range
        queryset = Registration.objects.all()

        if from_date:
            queryset = queryset.filter(date__gte=from_date)
        if to_date:
            queryset = queryset.filter(date__lte=to_date)

        # Serialize the data
        serializer = RegistrationSerializer(queryset, many=True)

        return Response(serializer.data, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

from django.utils.timezone import make_aware
from ..serializers import RegistrationSerializer, PatientAttendanceSerializer

@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_all_patient_details(request):
    patients = Registration.objects.all()
    # print(patients)
    serializer = RegistrationSerializer(patients, many=True)
    return Response(serializer.data)

