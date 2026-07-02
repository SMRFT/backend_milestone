from bson import ObjectId
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

@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([HasRolePermission])
def therapy_type_detail(request, pk):
    try:
        instance = TherapyDetails.objects.get(_id=ObjectId(pk))
    except (TherapyDetails.DoesNotExist, Exception):
        try:
            instance = TherapyDetails.objects.get(pk=pk)
        except TherapyDetails.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = TherapyDetailsSerializer(instance)
        return Response(serializer.data)

    elif request.method == "PATCH":
        serializer = TherapyDetailsSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(
                lastmodified_by=request.data.get('auth-user-id'),
                lastmodified_date=timezone.now()
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# --- Domains ---
@api_view(["GET", "POST"])
@permission_classes([HasRolePermission])
def domain_list_create(request):
    if request.method == "GET":
        therapy_id = request.query_params.get('therapy_type')
        if therapy_id:
            from django.db.models import Q
            from bson import ObjectId
            normalized_therapy_id = therapy_id
            if len(therapy_id) == 24:
                try:
                    therapy_obj = TherapyDetails.objects.get(_id=ObjectId(therapy_id))
                    normalized_therapy_id = therapy_obj.therapy_id
                except: pass
            qs = GoalDomain.objects.filter(Q(therapy_type=normalized_therapy_id) | Q(therapy_type=therapy_id))
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

@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([HasRolePermission])
def domain_detail(request, pk):
    try:
        instance = GoalDomain.objects.get(_id=ObjectId(pk))
    except (GoalDomain.DoesNotExist, Exception):
        try:
            instance = GoalDomain.objects.get(pk=pk)
        except GoalDomain.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = GoalDomainSerializer(instance)
        return Response(serializer.data)

    elif request.method == "PATCH":
        serializer = GoalDomainSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(
                lastmodified_by=request.data.get('auth-user-id'),
                lastmodified_date=timezone.now()
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# --- Levels ---
@api_view(["GET", "POST"])
@permission_classes([HasRolePermission])
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

@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([HasRolePermission])
def level_detail(request, pk):
    try:
        instance = GoalLevel.objects.get(_id=ObjectId(pk))
    except (GoalLevel.DoesNotExist, Exception):
        try:
            instance = GoalLevel.objects.get(pk=pk)
        except GoalLevel.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = GoalLevelSerializer(instance)
        return Response(serializer.data)

    elif request.method == "PATCH":
        serializer = GoalLevelSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(
                lastmodified_by=request.data.get('auth-user-id'),
                lastmodified_date=timezone.now()
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# --- Goal Library ---
@api_view(["GET", "POST"])
@permission_classes([HasRolePermission])
def goal_library_list_create(request):
    if request.method == "GET":
        domain_id = request.query_params.get('domain')
        therapy_id = request.query_params.get('therapy_type')
        is_custom = request.query_params.get('is_custom')
        
        qs = GoalLibrary.objects.all()
        if domain_id: qs = qs.filter(domain=domain_id)
        if therapy_id: qs = qs.filter(therapy_type=therapy_id)
        if is_custom is not None:
            is_custom_bool = is_custom.lower() in ['true', '1']
            qs = qs.filter(is_custom__in=[is_custom_bool])
            
        serializer = GoalLibrarySerializer(qs, many=True)
        return Response(serializer.data)
    
    if request.method == "POST":
        serializer = GoalLibrarySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.data.get('auth-user-id'))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([HasRolePermission])
def goal_library_detail(request, pk):
    try:
        instance = GoalLibrary.objects.get(_id=ObjectId(pk))
    except (GoalLibrary.DoesNotExist, Exception):
        try:
            instance = GoalLibrary.objects.get(pk=pk)
        except GoalLibrary.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = GoalLibrarySerializer(instance)
        return Response(serializer.data)

    elif request.method == "PATCH":
        serializer = GoalLibrarySerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            # Reset goal_no on edit if domain changed so it regenerates automatically
            if 'domain' in request.data and request.data['domain'] != instance.domain:
                instance.goal_no = ""
            serializer.save(
                lastmodified_by=request.data.get('auth-user-id'),
                lastmodified_date=timezone.now()
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
