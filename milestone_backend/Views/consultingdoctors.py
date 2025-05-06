from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ..models import ConsultingDoctor
import json
from rest_framework.decorators import api_view , permission_classes
from ..auth.permissions import SkipPermissionsIfDisabled
from pyauth.auth import HasRoleAndDataPermission

@csrf_exempt
@api_view(['POST'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def save_consulting_doctor(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            doctor = ConsultingDoctor.objects.create(
                name=data.get('name'),
                designation=data.get('designation'),
                phone=data.get('phone'),
                address=data.get('address')
            )
            return JsonResponse({
                'success': True,
                'doctor_id': str(doctor.id),  # Convert ObjectId to string
                'message': 'Doctor added successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)



@csrf_exempt
def get_consulting_doctors(request):
    doctors = ConsultingDoctor.objects.all().values()
    return JsonResponse(list(doctors), safe=False)