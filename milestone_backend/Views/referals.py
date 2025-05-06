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

from ..auth.permissions import SkipPermissionsIfDisabled
from pyauth.auth import HasRoleAndDataPermission

@api_view(['POST'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def register_referral_doctor(request):
    if request.method == 'POST':
        serializer = ReferralDoctorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Referral Doctor registered successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_referral_doctors(request):
    if request.method == 'GET':
        doctors = ReferralDoctor.objects.all()
        serializer = ReferralDoctorSerializer(doctors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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