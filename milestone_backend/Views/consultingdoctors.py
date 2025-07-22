from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ..models import ConsultingDoctor
import json
from rest_framework.decorators import api_view , permission_classes
from pyauth.auth import HasRolePermission
from ..serializers import ConsultingDoctorSerializer
from rest_framework.response import Response
from rest_framework import status, serializers
from django.http import JsonResponse
from datetime import datetime
from pymongo import MongoClient
import os


@api_view(['POST'])
@permission_classes([HasRolePermission])  # Add your permission class here
def save_consulting_doctor(request):
    if request.method == 'POST':
        print("=== DEBUG INFO ===")
        print("Request data:", request.data)
        print("Content type:", request.content_type)
        
        # Get the authenticated user's ID from the request
        auth_user_id = request.data.get('auth-user-id')
        print("Auth User ID:", auth_user_id)
        
        # Create serializer with context containing the auth_user_id
        serializer = ConsultingDoctorSerializer(
            data=request.data, 
            context={'auth_user_id': auth_user_id}
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
                "success": True,
                "message": "Consulting Doctor added successfully!",
                "doctor_id": str(doctor.id),
                "doctor_name": doctor.name
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            print("Save error:", str(e))
            print("Exception type:", type(e))
            import traceback
            print("Traceback:", traceback.format_exc())
            return Response({
                "success": False,
                "error": "Failed to save doctor", 
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': False, 
        'error': 'Method not allowed'
    }, status=status.HTTP_405_METHOD_NOT_ALLOWED)

@api_view(['PATCH'])
@permission_classes([HasRolePermission])
def update_consulting_doctor(request, employee_id):
    """
    Update registration with automatic audit field population using employee_id
    """
    try:
        # MongoDB connection setup
        mongo_uri = os.environ.get("MILESTONE_DB_HOST")
        db_name = os.environ.get("MILESTONE_DB_NAME", "Milestone")
        collection_name = "milestone_backend_consultingdoctor"  # Assuming this is the collection name
        
        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        db = client[db_name]
        collection = db[collection_name]
        
        # Find the document by employee_id
        registration_doc = collection.find_one({"employee_id": employee_id})
        
        if not registration_doc:
            return Response(
                {'error': 'Doctor not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Extract employee ID from request
        user_id = request.data.get('auth-user-id')
        
        # Prepare update data
        update_data = {}
        
        # Add fields from request data (excluding system fields)
        excluded_fields = ['_id', 'created_at', 'lastmodified_date', 'lastmodified_by']
        for key, value in request.data.items():
            if key not in excluded_fields:
                update_data[key] = value
        
        # Add audit fields
        update_data['lastmodified_date'] = datetime.now()
        if user_id:
            update_data['lastmodified_by'] = user_id
        
        # Perform the update
        result = collection.update_one(
            {"employee_id": employee_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            # Fetch the updated document
            updated_doc = collection.find_one({"employee_id": employee_id})
            
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
@csrf_exempt
def get_consulting_doctors(request):
    doctors = ConsultingDoctor.objects.all().values()
    return JsonResponse(list(doctors), safe=False)