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
from pyauth.auth import HasRolePermission
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_404
from pymongo import DESCENDING, MongoClient
import gridfs

import os
import certifi
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

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from datetime import datetime
from ..models import Registration, PatientAssessment, PatientAttendance
from ..serializers import RegistrationSerializer

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
@permission_classes([HasRolePermission])
def get_all_attendance_patients(request):
    patients = Registration.objects.all()
    attendances = PatientAttendance.objects.filter()

    # Map patient registration_number -> list of attendances
    attendance_map = {}
    for att in attendances:
        reg_no = att.registration_number
        if reg_no not in attendance_map:
            attendance_map[reg_no] = []
        attendance_map[reg_no].append(att)

    response_data = []

    for patient in patients:
        patient_info = RegistrationSerializer(patient).data
        reg_no = patient_info.get("registration_number")

        patient_attendances = attendance_map.get(reg_no, [])

        if patient_attendances:
            for att in patient_attendances:
                response_data.append({
                    **patient_info,
                    "attendances": [{
                        "date": att.date.strftime("%Y-%m-%d") if att.date else None,
                        "session": att.session,
                        "therapy_charge": att.therapy_charge,
                        "_id": str(att.id) if att.id else "None",
                    }],
                    "total_therapy_charge": att.therapy_charge,
                    "total_sessions": att.session
                })
        # else:
        #     # Patient with no attendance
        #     response_data.append({
        #         **patient_info,
        #         "attendances": [],
        #         "therapy_charge": 0,
        #         "sessions": 0
        #     })

    return Response(response_data)

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
            "age": patient.age,
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

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils.timezone import make_aware
from datetime import datetime
from ..models import Registration, PatientAttendance
from ..serializers import RegistrationSerializer, PatientAttendanceSerializer

@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_all_patient_details(request):
    patients = Registration.objects.all()
    # print(patients)
    serializer = RegistrationSerializer(patients, many=True)
    return Response(serializer.data)

from datetime import datetime, timedelta

from datetime import datetime, timedelta, date
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from milestone_backend.models import PatientAttendance
from milestone_backend.serializers import PatientAttendanceSerializer

@api_view(['POST'])
@permission_classes([HasRolePermission])
def add_patient_attendance(request):
    employee_id = request.data.get('auth-user-id')
    registration_number = request.data.get('registration_number')
    date_str = request.data.get('date')

    if not registration_number or not date_str:
        return Response(
            {"error": "registration_number and date are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Parse date
    try:
        date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return Response(
            {"error": "Invalid date format. Use ISO format."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # First and last day of the month
    first_day = date_obj.replace(day=1)
    if date_obj.month == 12:
        last_day = date_obj.replace(year=date_obj.year + 1, month=1, day=1) - timedelta(seconds=1)
    else:
        last_day = date_obj.replace(month=date_obj.month + 1, day=1) - timedelta(seconds=1)

    # Check for existing attendance in same month
    existing_attendance = PatientAttendance.objects.filter(
        registration_number=registration_number,
        date__gte=first_day,
        date__lte=last_day,
        is_active=True
    ).first()

    if existing_attendance:
        return Response(
            {"error": "Attendance for this patient already exists for this month."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Add audit fields before saving
    serializer = PatientAttendanceSerializer(data=request.data)
    if serializer.is_valid():
        instance = serializer.save(
            created_by=employee_id,
            lastmodified_by=employee_id,
            lastmodified_date=datetime.now()
        )
        return Response(PatientAttendanceSerializer(instance).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from pymongo import MongoClient
from bson import ObjectId
import os

MONGO_URI = os.environ.get("GLOBAL_DB_HOST")
DB_NAME = os.environ.get("MILESTONE_DB_NAME", "Milestone")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

attendance_col = db["milestone_backend_patientattendance"]
registration_col = db["milestone_backend_registration"]

@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_all_patient_attendance(request):
    # MongoDB collections
    mongo_uri = os.environ.get("GLOBAL_DB_HOST")
    client = MongoClient(mongo_uri)
    db = client["Milestone"]
    attendance_col = db['milestone_backend_patientattendance']
    registration_col = db['milestone_backend_registration']

    # Only active records
    attendances = list(attendance_col.find({"is_active": True}).sort("date", -1))
    
    # Fetch all registrations once
    registrations = {r["registration_number"]: r for r in registration_col.find()}

    # Combine attendance with registration info
    combined_data = []
    for a in attendances:
        reg_data = registrations.get(a["registration_number"], {})

        # Handle dob correctly
        dob_value = reg_data.get("dob", None)
        if isinstance(dob_value, dict):
            dob = dob_value.get("$date", None)
        elif hasattr(dob_value, "isoformat"):  # datetime object
            dob = dob_value.isoformat()
        else:
            dob = None

        combined_data.append({
            "_id": str(a["_id"]),
            "registration_number": a["registration_number"],
            "date": a.get("date", None),
            "session": a.get("session", ""),
            "therapy_charge": a.get("therapy_charge", 0),
            "name_of_child": reg_data.get("name_of_child", ""),
            "dob": dob,
            "sex": reg_data.get("sex", ""),
        })

    return Response(combined_data, status=status.HTTP_200_OK)

@api_view(['PATCH'])
@permission_classes([HasRolePermission])
def edit_patient_attendance(request):
    employee_id = request.data.get('auth-user-id')
    record_id = request.data.get("_id")

    if not record_id:
        return Response({"error": "_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        obj_id = ObjectId(record_id)
    except Exception:
        return Response({"error": "Invalid _id"}, status=status.HTTP_400_BAD_REQUEST)

    allowed_fields = ["session", "therapy_charge"]
    update_data = {f: request.data[f] for f in allowed_fields if f in request.data}

    if not update_data:
        return Response({"error": "No valid fields to update"}, status=status.HTTP_400_BAD_REQUEST)

    # Add audit info for modification
    update_data.update({
        "lastmodified_by": employee_id,
        "lastmodified_date": datetime.now()
    })

    # Only update if record is active
    result = attendance_col.update_one(
        {"_id": obj_id, "is_active": True},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        return Response({"error": "Attendance not found or inactive"}, status=status.HTTP_404_NOT_FOUND)

    updated_doc = attendance_col.find_one({"_id": obj_id})
    updated_doc["_id"] = str(updated_doc["_id"])
    return Response({"message": "Updated successfully", "updated_record": updated_doc})

@api_view(['DELETE'])
@permission_classes([HasRolePermission])
def delete_patient_attendance(request):
    employee_id = request.data.get('auth-user-id')
    record_id = request.data.get("_id")

    if not record_id:
        return Response({"error": "_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        obj_id = ObjectId(record_id)
    except Exception:
        return Response({"error": "Invalid _id"}, status=status.HTTP_400_BAD_REQUEST)

    # Soft delete + audit tracking
    result = attendance_col.update_one(
        {"_id": obj_id, "is_active": True},
        {
            "$set": {
                "is_active": False,
                "lastmodified_by": employee_id,
                "lastmodified_date": datetime.now()
            }
        }
    )

    if result.matched_count == 0:
        return Response({"error": "Attendance not found or already inactive"}, status=status.HTTP_404_NOT_FOUND)

    return Response({"message": "Deleted successfully"})
