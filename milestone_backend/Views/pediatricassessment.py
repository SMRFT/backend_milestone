from ..serializers import RegistrationSerializer
from ..models import Registration, PatientAssessment
from rest_framework.response import Response
from datetime import datetime ,timedelta ,date
from rest_framework.decorators import api_view , permission_classes
from rest_framework import status
from ..models import PatientAssessment
from ..serializers import HistoryRecordingSheetSerializer
from django.db.models import Max
from django.http import JsonResponse
from ..models import Registration, HistoryRecordingSheet
from pyauth.auth import HasRolePermission
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_404
from pymongo import DESCENDING, MongoClient
import gridfs
import os
import certifi
from bson import ObjectId
from dotenv import load_dotenv
from ..serializers import HistoryRecordingSheetSerializer

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
def CreateHistoryRecordingSheet(request):
    if request.method == 'POST':
        serializer = HistoryRecordingSheetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([HasRolePermission])
def GetHistoryRecordingSheet(request):
    records = HistoryRecordingSheet.objects.all().order_by('-id')
    serializer = HistoryRecordingSheetSerializer(records, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
