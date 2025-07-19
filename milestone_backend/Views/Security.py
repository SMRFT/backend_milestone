from rest_framework.response import Response
from django.http import JsonResponse
from django.contrib.auth.hashers import check_password
from ..models import EmployeeRegistration
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view , permission_classes
from rest_framework.response import Response
from rest_framework import status
from ..serializers import EmployeeRegistrationSerializer
from django.contrib.auth.hashers import make_password
from pyauth.auth import HasRolePermission


@api_view(['POST'])
@permission_classes([HasRolePermission])
def employeeregistration(request):
    serializer = EmployeeRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        # Hash the password before saving
        serializer.validated_data['password'] = make_password(serializer.validated_data['password'])
        serializer.save()
        return Response({'message': 'Registration successful!'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

