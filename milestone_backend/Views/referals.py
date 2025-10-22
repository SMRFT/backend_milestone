from rest_framework.decorators import api_view , permission_classes
from rest_framework.response import Response
from rest_framework import status
from ..models import ReferralDoctor
from ..serializers import ReferralDoctorSerializer
from rest_framework.response import Response
from django.http import JsonResponse
from datetime import datetime
from ..models import Registration
from ..serializers import RegistrationSerializer
from pyauth.auth import HasRolePermission
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import os
import logging
logger = logging.getLogger(__name__)
from django.db.models import Q
from datetime import datetime
from django.utils.dateparse import parse_date


@api_view(['POST'])
@permission_classes([HasRolePermission])
def register_referral_doctor(request):
    if request.method == 'POST':
        print("=== DEBUG INFO ===")
        print("Request data:", request.data)
        print("Content type:", request.content_type)
        
        employee_id = request.data.get('auth-user-id')
        print("Employee ID:", employee_id)
        
        serializer = ReferralDoctorSerializer(
            data=request.data, 
            context={'employee_id': employee_id}
        )
        
        print("Serializer valid:", serializer.is_valid())
        if not serializer.is_valid():
            print("Serializer errors:", serializer.errors)
            return Response({
                "error": "Validation failed", 
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            doctor = serializer.save()
            print("Doctor saved successfully:", doctor.id)
            return Response({
                "message": "Referral Doctor registered successfully!",
                "referral_id": doctor.referral_id,
                "doctor_name": doctor.doctor_name
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            print("Save error:", str(e))
            print("Exception type:", type(e))
            import traceback
            print("Traceback:", traceback.format_exc())
            return Response({
                "error": "Failed to save", 
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PATCH'])
@permission_classes([HasRolePermission])
def update_doctor(request, referral_id):
    """
    Update registration with automatic audit field population using referral_id
    """
    try:
        # MongoDB connection setup
        mongo_uri = os.environ.get("GLOBAL_DB_HOST")
        db_name = os.environ.get("MILESTONE_DB_NAME", "Milestone")
        collection_name = "milestone_backend_referraldoctor"  # Assuming this is the collection name
        
        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        db = client[db_name]
        collection = db[collection_name]
        
        # Find the document by referral_id
        registration_doc = collection.find_one({"referral_id": referral_id})
        
        if not registration_doc:
            return Response(
                {'error': 'Doctor not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Extract employee ID from request
        employee_id = request.data.get('auth-user-id')
        
        # Prepare update data
        update_data = {}
        
        # Add fields from request data (excluding system fields)
        excluded_fields = ['_id', 'created_at', 'lastmodified_date', 'lastmodified_by']
        for key, value in request.data.items():
            if key not in excluded_fields:
                update_data[key] = value
        
        # Add audit fields
        update_data['lastmodified_date'] = datetime.now()
        if employee_id:
            update_data['lastmodified_by'] = employee_id
        
        # Perform the update
        result = collection.update_one(
            {"referral_id": referral_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            # Fetch the updated document
            updated_doc = collection.find_one({"referral_id": referral_id})
            
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


@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_referral_doctors(request):
    if request.method == 'GET':
        doctors = ReferralDoctor.objects.all()
        serializer = ReferralDoctorSerializer(doctors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

