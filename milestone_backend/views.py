from rest_framework.decorators import api_view , permission_classes
from django.db.models import Count
from datetime import datetime, timedelta , time
import pytz
from rest_framework.response import Response
from rest_framework import status
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

#models
from .models import SkillTestResult
from .models import PediatricAssessment
from .models import Registration
from .models import PediatricAssessment
from .models import PatientAssessment

#serializers
from .serializers import RegistrationSerializer,PatientAssessmentSerializer,PediatricAssessmentSerializer
from .serializers import PatientAssessmentSerializer

from .auth.permissions import SkipPermissionsIfDisabled
from pyauth.auth import HasRoleAndDataPermission

@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_patients_report(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if not start_date_str or not end_date_str:
        return Response({"error": "Start date and end date are required."}, status=400)

    # Parse dates
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    # Ensure time is set to the start and end of the day
    start_date = datetime.combine(start_date, time.min)  # 00:00:00
    end_date = datetime.combine(end_date, time.max)  # 23:59:59

    # Filter patients by date range
    patients = Registration.objects.filter(date__range=[start_date, end_date])

    # Calculate total patients in the selected date range
    total_patients = patients.count()

    # Calculate daily counts
    daily_counts = (
        patients.values('date')
        .annotate(total_cases=Count('id'))
        .order_by('date')
    )

    # Calculate monthly counts
    monthly_counts = (
        patients.values('date__month')
        .annotate(total_cases=Count('id'))
        .order_by('date__month')
    )

    # Serialize patient data
    serializer = RegistrationSerializer(patients, many=True)

    return Response({
        'total_patients': total_patients,  # Added total patients count
        'patients': serializer.data,
        'daily_counts': daily_counts,
        'monthly_counts': monthly_counts
    })



@api_view(['GET', 'POST'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def PediatricAssessmentView(request):
    if request.method == 'POST':
        serializer = PediatricAssessmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# GET method to retrieve all pediatric assessments
@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def pediatric_assessment_list(request):
    if request.method == 'GET':
        assessments = PediatricAssessment.objects.all()  # Fetch all records
        serializer = PediatricAssessmentSerializer(assessments, many=True)  # Serialize list of assessments
        return Response(serializer.data)



logger = logging.getLogger(__name__)
@csrf_exempt
@require_http_methods(["POST", "GET"])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def save_patient_skilltest(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            logger.debug(f"Received data: {data}")
            registration_number = data.get('registration_number')
            patient_name = data.get('patient_name')
            age = data.get('age')
            sex = data.get('sex')
            status = data.get('data', {}).get('status')
            category = data.get('data', {}).get('category')
            selected_questions = data.get('data', {}).get('selected_questions', [])
            comment = data.get('data', {}).get('comment', '')
            date = data.get('date')
            
            if date:
               date = datetime.fromisoformat(date).date()  # Parse ISO 8601 date format
            else:
                date = None  # or use current date: datetime.now().date()
                

            data_dict = {
                "status": status,
                "category": category,
                "selected_questions": selected_questions,
                "comment": comment,
            }
            
            skill_test_result = SkillTestResult(
                registration_number=registration_number,
                patient_name=patient_name,
                age=age,
                sex=sex,
                date=date,
                data=data_dict
            )
            
            logger.debug(f"Data to be saved: {skill_test_result}")
            skill_test_result.save()
            
            return JsonResponse({'message': 'Data saved successfully!'}, status=201)
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)


# Function to convert string to UTC datetime object
def str_to_date_utc(date_str, is_end_of_day=False):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        if is_end_of_day:
            # Set to end of the day (23:59:59)
            date_obj += timedelta(days=1) - timedelta(seconds=1)
        # Convert to UTC timezone
        return pytz.utc.localize(date_obj)
    except ValueError:
        return None

# Fetch patient assessments using Django ORM with date filtering
def get_patient_assessments(request):
    from_date_str = request.GET.get('from_date')  # Get the 'from_date' query parameter
    to_date_str = request.GET.get('to_date')  # Get the 'to_date' query parameter

    # Convert to UTC datetime objects
    from_date = str_to_date_utc(from_date_str) if from_date_str else None
    to_date = str_to_date_utc(to_date_str, is_end_of_day=True) if to_date_str else None

    try:
        # Prepare the query filter
        query_filter = {}

        # Apply date filtering if both from_date and to_date are provided
        if from_date and to_date:
            query_filter["date__range"] = (from_date, to_date)
        elif from_date:
            query_filter["date__gte"] = from_date
        elif to_date:
            query_filter["date__lte"] = to_date

        # Fetch records using Django ORM
        assessments = PatientAssessment.objects.filter(**query_filter)

        # Serialize the data
        serializer = PatientAssessmentSerializer(assessments, many=True)

        # Get the total count of patients (number of records)
        total_count = assessments.count()

        return JsonResponse({
            'status': 'success',
            'data': serializer.data,
            'total_count': total_count
        }, safe=False)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
