from ..serializers import RegistrationSerializer
from ..models import Registration, PatientAssessment
from rest_framework.response import Response
from datetime import datetime
from rest_framework.decorators import api_view , permission_classes
from rest_framework.response import Response
from rest_framework import status
from ..models import PatientAssessment
from ..serializers import PatientAssessmentSerializer
from django.db.models import Max
from django.http import JsonResponse
from pymongo import MongoClient
from django.http import JsonResponse
from ..models import Registration
from ..auth.permissions import SkipPermissionsIfDisabled
from pyauth.auth import HasRoleAndDataPermission
import gridfs

import os
import certifi
from dotenv import load_dotenv

load_dotenv()  # Load from .env if present

env_type = os.environ.get("ENV_CLASSIFICATION", "local")

mongo_uri = os.environ.get("GLOBAL_DB_HOST")
db_name = os.environ.get("MILESTONE_DB_NAME")

if env_type == "test":
    client = MongoClient(mongo_uri)
else:
    client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())

@api_view(['POST'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def create_registration(request):
    serializer = RegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save()  # Automatically calls the save() method in your model to generate the registration number
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])    
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
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def save_assessments(request):
    if request.method == 'POST':
        serializer = PatientAssessmentSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()  # Save the new patient assessment to the database
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    



@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_assessments(request):
    # Retrieve all patient assessments
    assessments = PatientAssessment.objects.all()
    
    # Serialize all the assessments
    serializer = PatientAssessmentSerializer(assessments, many=True)
    
    # Return the serialized data as a response
    return Response(serializer.data, status=status.HTTP_200_OK)




# To get the next registration number
@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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
            "age": patient.age,
            "sex": patient.sex,
            # other fields...
        })
    except Registration.DoesNotExist:
        return JsonResponse({"error": "Patient not found"}, status=404)