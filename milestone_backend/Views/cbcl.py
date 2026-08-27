from django.utils import timezone
from rest_framework.response import Response
from rest_framework.decorators import api_view , permission_classes
from rest_framework import status
from ..models import CBCL
from ..serializers import CBCLSerializer
from pyauth.auth import HasRolePermission



@api_view(['POST'])
@permission_classes([HasRolePermission])
def submit_cbcl(request):
    if request.method == 'POST':
        serializer = CBCLSerializer(data=request.data)
        
        if serializer.is_valid():
            employee_id = request.data.get("auth-user-id")
            serializer.save(created_by=employee_id, created_date=timezone.now())
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_cbcl_data(request, childName=None):
    try:
        from_date = request.GET.get('from_date') or request.GET.get('fromDate')
        to_date = request.GET.get('to_date') or request.GET.get('toDate')

        cbcl_data = CBCL.objects.all()

        if childName:
            filtered = cbcl_data.filter(childName__iexact=childName)
            if not filtered.exists():
                filtered = cbcl_data.filter(childName__icontains=childName)
            cbcl_data = filtered

        if from_date:
            cbcl_data = cbcl_data.filter(dateOfAssessment__gte=from_date)
        if to_date:
            cbcl_data = cbcl_data.filter(dateOfAssessment__lte=to_date)

        serializer = CBCLSerializer(cbcl_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
