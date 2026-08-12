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
from .models import SkillTestResult
from .models import PediatricAssessment
from .models import Registration
from .models import PediatricAssessment
from .models import PatientAssessment
from .serializers import RegistrationSerializer,PatientAssessmentSerializer,PediatricAssessmentSerializer,HistoryRecordingSheetSerializer
from .serializers import PatientAssessmentSerializer
from pyauth.auth import HasRolePermission

@api_view(['GET'])
@permission_classes([HasRolePermission])
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
@permission_classes([HasRolePermission])
def PediatricAssessmentView(request):
    if request.method == 'POST':
        serializer = PediatricAssessmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# GET method to retrieve all pediatric assessments
@api_view(['GET'])
@permission_classes([HasRolePermission])
def pediatric_assessment_list(request):
    if request.method == 'GET':
        assessments = PediatricAssessment.objects.all()  # Fetch all records
        serializer = PediatricAssessmentSerializer(assessments, many=True)  # Serialize list of assessments
        return Response(serializer.data)



logger = logging.getLogger(__name__)
@csrf_exempt
@require_http_methods(["POST", "GET"])
@permission_classes([HasRolePermission])
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
@api_view(['GET'])
@permission_classes([HasRolePermission])
@csrf_exempt
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
    


from datetime import datetime

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import CrossConsultationPlan, CrossTherapyRecommendation, RECOMMENDATION_ROLES
from .serializers import CrossConsultationPlanSerializer, CrossTherapyRecommendationSerializer


def _filter_by_date_month(rows, date_field, date_str, month_str, year_str):
    """
    rows: list of dicts each containing a date_field like 'date'
    date_str: exact date filter, e.g. '2026-06-10'
    month_str: '1'..'12'
    year_str: '2026'
    """
    if not (date_str or month_str or year_str):
        return rows

    filtered = []
    for row in rows:
        raw = row.get(date_field)
        if not raw:
            continue
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue

        if date_str and parsed.isoformat() != date_str:
            continue
        if month_str and str(parsed.month) != str(int(month_str)):
            continue
        if year_str and str(parsed.year) != str(year_str):
            continue
        filtered.append(row)
    return filtered


# ---------------------------------------------------------------------------
# Cross Consultation & Follow-up Plan
# ---------------------------------------------------------------------------

@api_view(["GET"])
def get_cross_consultation_plan(request, registration_number):
    """
    GET /cross-consultation/<registration_number>/?date=YYYY-MM-DD&month=6&year=2026
    Returns the plan record for a patient, entries optionally filtered by date/month/year.
    """
    try:
        plan = CrossConsultationPlan.objects.get(registration_number=registration_number)
    except CrossConsultationPlan.DoesNotExist:
        return Response(
            {"registration_number": registration_number, "patient_name": "", "age_sex": "", "entries": []},
            status=status.HTTP_200_OK,
        )

    serializer = CrossConsultationPlanSerializer(plan)
    data = serializer.data
    data["entries"] = _filter_by_date_month(
        data.get("entries", []),
        "date",
        request.query_params.get("date"),
        request.query_params.get("month"),
        request.query_params.get("year"),
    )
    return Response(data, status=status.HTTP_200_OK)


@api_view(["POST"])
def create_cross_consultation_plan(request):
    """
    POST /cross-consultation/
    Creates the plan record for a patient (called once, first time a patient gets a plan).
    Body: { registration_number, patient_name, age_sex, entries: [...], created_by }
    """
    registration_number = request.data.get("registration_number")
    if CrossConsultationPlan.objects.filter(registration_number=registration_number).exists():
        return Response(
            {"detail": "A plan already exists for this patient. Use PATCH to add entries."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    employee_id = request.data.get("created_by")
    serializer = CrossConsultationPlanSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(created_by=employee_id, lastmodified_by=employee_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PATCH"])
def update_cross_consultation_plan(request, registration_number):
    """
    PATCH /cross-consultation/<registration_number>/
    Appends a new { date, plan } entry to the patient's plan.
    Body: { date: "2026-06-10", plan: "Behaviour modification to be started", created_by }
    """
    try:
        plan = CrossConsultationPlan.objects.get(registration_number=registration_number)
    except CrossConsultationPlan.DoesNotExist:
        return Response({"detail": "No plan found for this patient."}, status=status.HTTP_404_NOT_FOUND)

    employee_id = request.data.get("created_by")
    new_entry = {
        "date": request.data.get("date"),
        "plan": request.data.get("plan"),
        "created_by": employee_id,
        "created_date": datetime.utcnow().isoformat(),
    }
    if not new_entry["date"] or not new_entry["plan"]:
        return Response({"detail": "'date' and 'plan' are required."}, status=status.HTTP_400_BAD_REQUEST)

    entries = plan.entries or []
    entries.append(new_entry)
    plan.entries = entries
    plan.lastmodified_by = employee_id
    plan.save()

    serializer = CrossConsultationPlanSerializer(plan)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Cross Therapy Recommendation Form
# ---------------------------------------------------------------------------

@api_view(["GET"])
def get_cross_therapy_recommendation(request, registration_number):
    """
    GET /cross-therapy-recommendation/<registration_number>/?date=YYYY-MM-DD&month=6&year=2026
    """
    try:
        rec = CrossTherapyRecommendation.objects.get(registration_number=registration_number)
    except CrossTherapyRecommendation.DoesNotExist:
        return Response(
            {
                "registration_number": registration_number,
                "patient_name": "",
                "age_sex": "",
                "recommendations": [],
                "roles": RECOMMENDATION_ROLES,
            },
            status=status.HTTP_200_OK,
        )

    serializer = CrossTherapyRecommendationSerializer(rec)
    data = serializer.data
    data["recommendations"] = _filter_by_date_month(
        data.get("recommendations", []),
        "date",
        request.query_params.get("date"),
        request.query_params.get("month"),
        request.query_params.get("year"),
    )
    data["roles"] = RECOMMENDATION_ROLES
    return Response(data, status=status.HTTP_200_OK)


@api_view(["POST"])
def create_cross_therapy_recommendation(request):
    """
    POST /cross-therapy-recommendation/
    Body: { registration_number, patient_name, age_sex, recommendations: [...], created_by }
    """
    registration_number = request.data.get("registration_number")
    if CrossTherapyRecommendation.objects.filter(registration_number=registration_number).exists():
        return Response(
            {"detail": "A recommendation record already exists for this patient. Use PATCH to add rows."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    employee_id = request.data.get("created_by")
    serializer = CrossTherapyRecommendationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(created_by=employee_id, lastmodified_by=employee_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PATCH"])
def update_cross_therapy_recommendation(request, registration_number):
    """
    PATCH /cross-therapy-recommendation/<registration_number>/
    Appends a new { recommendation_by, recommendation, date } row.
    Body: { recommendation_by: "Special Educator", recommendation: "...", date: "2026-06-09", created_by }
    """
    try:
        rec = CrossTherapyRecommendation.objects.get(registration_number=registration_number)
    except CrossTherapyRecommendation.DoesNotExist:
        return Response({"detail": "No recommendation record found for this patient."}, status=status.HTTP_404_NOT_FOUND)

    role = request.data.get("recommendation_by")
    if role not in RECOMMENDATION_ROLES:
        return Response(
            {"detail": f"'recommendation_by' must be one of: {', '.join(RECOMMENDATION_ROLES)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    employee_id = request.data.get("created_by")
    new_row = {
        "recommendation_by": role,
        "recommendation": request.data.get("recommendation", ""),
        "date": request.data.get("date"),
        "created_by": employee_id,
        "created_date": datetime.utcnow().isoformat(),
    }

    recommendations = rec.recommendations or []
    recommendations.append(new_row)
    rec.recommendations = recommendations
    rec.lastmodified_by = employee_id
    rec.save()

    serializer = CrossTherapyRecommendationSerializer(rec)
    return Response(serializer.data, status=status.HTTP_200_OK)
    


from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import CrossTherapyRecommendation
from .serializers import CrossTherapyRecommendationSerializer

@api_view(['POST'])
def save_cross_therapy_recommendation(request):
    registration_number = request.data.get('registration_number')
    if not registration_number:
        return Response(
            {"error": "registration_number is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    existing = CrossTherapyRecommendation.objects.filter(
        registration_number=registration_number
    ).first()

    if existing:
        serializer = CrossTherapyRecommendationSerializer(
            existing, data=request.data, partial=True
        )
        if serializer.is_valid():
            CrossTherapyRecommendation.objects.filter(
                registration_number=registration_number
            ).update(**serializer.validated_data)
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer = CrossTherapyRecommendationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_cross_therapy_recommendation(request, registration_number):
    record = CrossTherapyRecommendation.objects.filter(
        registration_number=registration_number
    ).first()
    if not record:
        return Response({}, status=status.HTTP_200_OK)
    serializer = CrossTherapyRecommendationSerializer(record)
    return Response(serializer.data, status=status.HTTP_200_OK)