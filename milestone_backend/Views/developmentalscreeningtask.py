from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from pymongo import MongoClient
from urllib.parse import quote_plus
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from rest_framework.decorators import api_view , permission_classes
from ..auth.permissions import SkipPermissionsIfDisabled
from pyauth.auth import HasRoleAndDataPermission
from pymongo import MongoClient
import gridfs

import os
import certifi
from dotenv import load_dotenv

load_dotenv()  # Load from .env if present

env_type = os.environ.get("ENV_CLASSIFICATION", "local")

mongo_uri = os.environ.get("GLOBAL_DB_HOST")
db_name = os.environ.get("MILESTONE_DB_NAME")

if env_type in ["test", "prod"]:
    client = MongoClient(mongo_uri)
else:
    client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())


@require_GET
@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def DevelopmentalTask(request):
    # URL-encode the password¸
    # Use f-string to inject the encoded password into the connection string
    db = client[db_name]          
    fs = gridfs.GridFS(db)
    collection = db['milestone_backend_developmental_screening']  # Access the 'Testdetails' collection
    # Fetch all test details from the collection
    test_details = list(collection.find({}, {"_id": 0}))  # Exclude '_id' field if not needed
    return JsonResponse(test_details, safe=False)




from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from milestone_backend.models import DevelopmentalScreeningTask

@api_view(['POST'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def save_developmental_screening_tasks(request):
    if request.method == 'POST':
        data = request.data

        try:
            # Parse the date if it's not already a datetime object
            date_str = data.get('date')
            date = datetime.fromisoformat(date_str) if date_str else None

            # Save the data to the database
            task_data = data.get('tasks', {})
            developmental_task = DevelopmentalScreeningTask.objects.create(
                patient_name=data.get('patient_name', ""),
                age=data.get('age', "N/A"),
                gender=data.get('gender', "N/A"),
                CA=data.get('CA', "0 months"),
                DA=data.get('DA', "0 months"),
                dq_value=float(data.get('dq_value', 0.00)),
                dq_classify=data.get('dq_classify', "Nil"),
                tasks=task_data,
                date=date,
            )

            return Response({"message": "Data saved successfully."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



from rest_framework.decorators import api_view
from rest_framework.response import Response
from ..models import DevelopmentalScreeningTask
from ..serializers import DevelopmentalScreeningTaskSerializer

@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_developmental_screening_tasks(request, patient_name=None):
    try:
        # Check if patient_name is provided as a URL parameter
        if patient_name:
            tasks = DevelopmentalScreeningTask.objects.filter(patient_name=patient_name)
        else:
            # Fallback to all tasks if no patient_name is provided
            tasks = DevelopmentalScreeningTask.objects.all()
        
        serializer = DevelopmentalScreeningTaskSerializer(tasks, many=True)
        return Response(serializer.data, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)
