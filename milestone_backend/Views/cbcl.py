from rest_framework.response import Response
from rest_framework.decorators import api_view , permission_classes
from rest_framework import status
from ..models import CBCL
from ..serializers import CBCLSerializer


from ..auth.permissions import SkipPermissionsIfDisabled
from pyauth.auth import HasRoleAndDataPermission



@api_view(['POST'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def submit_cbcl(request):
    if request.method == 'POST':
        serializer = CBCLSerializer(data=request.data)
        
        if serializer.is_valid():
            # Save the data to the database
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_cbcl_data(request, childName=None):
    try:
        # Check if childName is provided as a URL parameter
        if childName:
            cbcl_data = CBCL.objects.filter(childName=childName)
        else:
            # Fallback to all data if no patient_name is provided
            cbcl_data = CBCL.objects.all()

        serializer = CBCLSerializer(cbcl_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
