from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from ..models import TherapyDetails, GoalDomain, GoalLevel, GoalLibrary
from ..serializers import (
    TherapyDetailsSerializer, 
    GoalDomainSerializer, 
    GoalLevelSerializer, 
    GoalLibrarySerializer
)
from pyauth.auth import HasRolePermission

# --- Therapy Types (using TherapyDetails) ---
@api_view(["GET", "POST"])
# @permission_classes([HasRolePermission])
def therapy_type_list_create(request):
    if request.method == "GET":
        qs = TherapyDetails.objects.all().order_by('therapy_name')
        serializer = TherapyDetailsSerializer(qs, many=True)
        return Response(serializer.data)
    
    if request.method == "POST":
        serializer = TherapyDetailsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.data.get('auth-user-id'))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["DELETE"])
# @permission_classes([HasRolePermission])
def therapy_type_detail(request, pk):
    try:
        instance = TherapyDetails.objects.get(pk=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except TherapyDetails.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

# --- Domains ---
@api_view(["GET", "POST"])
# @permission_classes([HasRolePermission])
def domain_list_create(request):
    if request.method == "GET":
        therapy_id = request.query_params.get('therapy_type')
        if therapy_id:
            qs = GoalDomain.objects.filter(therapy_type=therapy_id)
        else:
            qs = GoalDomain.objects.all()
        serializer = GoalDomainSerializer(qs, many=True)
        return Response(serializer.data)
    
    if request.method == "POST":
        serializer = GoalDomainSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.data.get('auth-user-id'))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["DELETE"])
# @permission_classes([HasRolePermission])
def domain_detail(request, pk):
    try:
        instance = GoalDomain.objects.get(pk=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except GoalDomain.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

# --- Levels ---
@api_view(["GET", "POST"])
# @permission_classes([HasRolePermission])
def level_list_create(request):
    if request.method == "GET":
        qs = GoalLevel.objects.all()
        serializer = GoalLevelSerializer(qs, many=True)
        return Response(serializer.data)
    
    if request.method == "POST":
        serializer = GoalLevelSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.data.get('auth-user-id'))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["DELETE"])
# @permission_classes([HasRolePermission])
def level_detail(request, pk):
    try:
        instance = GoalLevel.objects.get(pk=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except GoalLevel.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

# --- Goal Library ---
@api_view(["GET", "POST"])
# @permission_classes([HasRolePermission])
def goal_library_list_create(request):
    if request.method == "GET":
        domain_id = request.query_params.get('domain')
        therapy_id = request.query_params.get('therapy_type')
        
        qs = GoalLibrary.objects.all()
        if domain_id: qs = qs.filter(domain=domain_id)
        if therapy_id: qs = qs.filter(therapy_type=therapy_id)
            
        serializer = GoalLibrarySerializer(qs, many=True)
        return Response(serializer.data)
    
    if request.method == "POST":
        serializer = GoalLibrarySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.data.get('auth-user-id'))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["DELETE"])
# @permission_classes([HasRolePermission])
def goal_library_detail(request, pk):
    try:
        instance = GoalLibrary.objects.get(pk=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except GoalLibrary.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
