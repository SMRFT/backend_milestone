from django.db.models import Count
from datetime import datetime, timedelta , time
import pytz
from rest_framework.response import Response
from rest_framework import status
import json
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from pyauth.auth import HasRolePermission
from dotenv import load_dotenv
import time
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt

load_dotenv()

from ..models import ClinicalPsychologyAssessment, OccupationalTherapyAssessment, SpeechTherapyAssessment, PhysiotherapyAssessment, PatientAssessment, AssessmentAnalysis, BehavioralObservationOption
from ..serializers import ClinicalPsychologyAssessmentSerializer, OccupationalTherapyAssessmentSerializer, SpeechTherapyAssessmentSerializer, PhysiotherapyAssessmentSerializer, AssessmentAnalysisSerializer, BehavioralObservationOptionSerializer


# -----------------------------------
# COMMON DATE FILTER
# -----------------------------------
from datetime import datetime, time

def filter_by_date(request):
    start = request.GET.get("start_date")
    end = request.GET.get("end_date")

    if not start or not end:
        return PatientAssessment.objects.none()

    # Convert to datetime with full day range
    start_datetime = datetime.combine(datetime.strptime(start, "%Y-%m-%d"), time.min)
    end_datetime = datetime.combine(datetime.strptime(end, "%Y-%m-%d"), time.max)

    return PatientAssessment.objects.filter(
        date__gte=start_datetime,
        date__lte=end_datetime
    )

from datetime import datetime

def get_employee_id(request):
    return (
        request.headers.get("auth-user-id")
        or request.data.get("auth-user-id")
    )


def save_with_audit(serializer, request):
    employee_id = get_employee_id(request)

    return serializer.save(
        created_by=employee_id,
        created_date=datetime.now()
    )


def update_with_audit(serializer, request):
    employee_id = get_employee_id(request)

    return serializer.save(
        lastmodified_by=employee_id,
        lastmodified_date=datetime.now()
    )


# -----------------------------------
# GET OT PATIENTS
# -----------------------------------
@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_ot_patients(request):
    queryset = filter_by_date(request)
    result = []

    for item in queryset:
        raw_assessment = item.assessments

        if not raw_assessment:
            continue

        try:
            assessments = json.loads(raw_assessment) if isinstance(raw_assessment, str) else raw_assessment
        except Exception:
            continue

        for a in assessments:
            if a.get("category") == "OT":
                result.append({
                    "billing_no": item.billing_no,
                    "patient_name": item.patient_name,
                    "registration_number": item.registration_number,
                    "age": item.age,
                    "sex": item.sex,
                    "phone": item.father_phone_number,
                    "assessment": a,
                    "date": item.date
                })
                break

    return Response({"otPatients": result}, status=status.HTTP_200_OK)


# -----------------------------------
# GET SPEECH PATIENTS
# -----------------------------------
@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_speech_patients(request):
    queryset = filter_by_date(request)
    result = []

    for item in queryset:
        raw_assessment = item.assessments

        if not raw_assessment:
            continue

        try:
            assessments = json.loads(raw_assessment) if isinstance(raw_assessment, str) else raw_assessment
        except Exception:
            continue

        for a in assessments:
            if a.get("category") == "Speech":
                result.append({
                    "billing_no": item.billing_no,
                    "patient_name": item.patient_name,
                    "registration_number": item.registration_number,
                    "age": item.age,
                    "sex": item.sex,
                    "phone": item.father_phone_number,
                    "assessment": a,
                    "date": item.date
                })
                break

    return Response({"speechPatients": result}, status=status.HTTP_200_OK)


# -----------------------------------
# GET PT PATIENTS
# -----------------------------------
@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_pt_patients(request):
    queryset = filter_by_date(request)
    result = []

    for item in queryset:
        raw_assessment = item.assessments

        if not raw_assessment:
            continue

        try:
            assessments = json.loads(raw_assessment) if isinstance(raw_assessment, str) else raw_assessment
        except Exception:
            continue

        for a in assessments:
            if a.get("category") == "PT":
                result.append({
                    "billing_no": item.billing_no,
                    "patient_name": item.patient_name,
                    "registration_number": item.registration_number,
                    "age": item.age,
                    "sex": item.sex,
                    "phone": item.father_phone_number,
                    "assessment": a,
                    "date": item.date
                })
                break

    return Response({"ptPatients": result}, status=status.HTTP_200_OK)


# -----------------------------------
# GET PSYCHOLOGICAL PATIENTS
# -----------------------------------
@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_psychological_patients(request):
    queryset = filter_by_date(request)
    result = []

    for item in queryset:
        raw_assessment = item.assessments

        if not raw_assessment:
            continue

        try:
            assessments = json.loads(raw_assessment) if isinstance(raw_assessment, str) else raw_assessment
        except Exception:
            continue

        for a in assessments:
            if a.get("category") == "Psychological":
                result.append({
                    "billing_no": item.billing_no,
                    "patient_name": item.patient_name,
                    "registration_number": item.registration_number,
                    "age": item.age,
                    "sex": item.sex,
                    "phone": item.father_phone_number,
                    "assessment": a,
                    "date": item.date
                })
                break

    return Response({"psychologicalPatients": result}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_all_category_patients(request):
    queryset = filter_by_date(request)
    result = []

    for item in queryset:
        raw_assessment = item.assessments

        try:
            assessments = (
                json.loads(raw_assessment)
                if isinstance(raw_assessment, str)
                else raw_assessment
            )
        except Exception:
            assessments = []

        # ❌ Exclude Consultation category
        filtered_assessments = [
            a for a in assessments
            if a.get("category") != "Consultation"
        ]

        # OPTIONAL: skip patient if no category left
        if not filtered_assessments:
            continue

        result.append({
            "billing_no": item.billing_no,
            "patient_name": item.patient_name,
            "registration_number": item.registration_number,
            "age": item.age,
            "sex": item.sex,
            "phone": item.father_phone_number,
            "assessments": filtered_assessments,
            "date": item.date
        })

    return Response(
        {"patients": result},
        status=status.HTTP_200_OK
    )


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([HasRolePermission])
def clinical_psychology_assessment(request):

    if request.method == 'GET':
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")

        items = ClinicalPsychologyAssessment.objects.filter(
            assessment_date__range=[from_date, to_date]
        ) if from_date and to_date else ClinicalPsychologyAssessment.objects.all()

        return Response(ClinicalPsychologyAssessmentSerializer(items, many=True).data)

    if request.method == 'POST':
        serializer = ClinicalPsychologyAssessmentSerializer(data=request.data)
        if serializer.is_valid():
            instance = save_with_audit(serializer, request)
            return Response(
                ClinicalPsychologyAssessmentSerializer(instance).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=400)

from bson import ObjectId
import datetime as dt
from .dbcollection import milestone_db

def sanitize_for_mongo(data):
    if isinstance(data, dict):
        return {k: sanitize_for_mongo(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_mongo(v) for v in data]
    elif isinstance(data, dt.date) and not isinstance(data, dt.datetime):
        return dt.datetime.combine(data, dt.time.min)
    return data

def update_assessment_record(model_class, serializer_class, request):
    record_id = request.data.get("id") or request.data.get("_id") or request.GET.get("id") or request.GET.get("_id")
    reg_num = request.data.get("registrationNumber") or request.data.get("registration_number")
    col_name = model_class._meta.db_table

    doc = None
    if record_id:
        try:
            doc = milestone_db[col_name].find_one({"_id": ObjectId(str(record_id))})
        except Exception:
            doc = None

    if not doc and reg_num:
        doc = milestone_db[col_name].find_one({"registrationNumber": reg_num})
        if not doc:
            doc = milestone_db[col_name].find_one({"registration_number": reg_num})

    if not doc:
        if not record_id and not reg_num:
            return Response({"error": "ID is required for update"}, status=400)
        return Response({"error": "Record not found"}, status=404)

    target_id = doc["_id"]

    serializer = serializer_class(data=request.data, partial=True)
    if serializer.is_valid():
        validated_data = dict(serializer.validated_data)
        employee_id = get_employee_id(request)
        validated_data["lastmodified_by"] = employee_id
        validated_data["lastmodified_date"] = datetime.now()

        mongo_payload = sanitize_for_mongo(validated_data)

        milestone_db[col_name].update_one(
            {"_id": target_id},
            {"$set": mongo_payload}
        )

        updated_doc = milestone_db[col_name].find_one({"_id": target_id})
        if updated_doc:
            if "_id" in updated_doc:
                updated_doc["_id"] = str(updated_doc["_id"])
                updated_doc["id"] = str(updated_doc["_id"])
            for k, v in list(updated_doc.items()):
                if isinstance(v, (datetime, dt.date)):
                    updated_doc[k] = v.isoformat()

        return Response(updated_doc, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([HasRolePermission])
def clinical_psychology_assessment(request):

    if request.method == 'GET':
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")

        items = ClinicalPsychologyAssessment.objects.filter(
            assessment_date__range=[from_date, to_date]
        ) if from_date and to_date else ClinicalPsychologyAssessment.objects.all()

        return Response(ClinicalPsychologyAssessmentSerializer(items, many=True).data)

    if request.method == 'POST':
        serializer = ClinicalPsychologyAssessmentSerializer(data=request.data)
        if serializer.is_valid():
            instance = save_with_audit(serializer, request)
            return Response(
                ClinicalPsychologyAssessmentSerializer(instance).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=400)

    if request.method == 'PUT':
        return update_assessment_record(ClinicalPsychologyAssessment, ClinicalPsychologyAssessmentSerializer, request)


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([HasRolePermission])
def occupational_therapy_assessment(request):

    if request.method == 'GET':
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")

        items = OccupationalTherapyAssessment.objects.filter(
            assessment_date__range=[from_date, to_date]
        ) if from_date and to_date else OccupationalTherapyAssessment.objects.all()

        return Response(OccupationalTherapyAssessmentSerializer(items, many=True).data)

    if request.method == 'POST':
        serializer = OccupationalTherapyAssessmentSerializer(data=request.data)
        if serializer.is_valid():
            instance = save_with_audit(serializer, request)
            return Response(
                OccupationalTherapyAssessmentSerializer(instance).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=400)

    if request.method == 'PUT':
        return update_assessment_record(OccupationalTherapyAssessment, OccupationalTherapyAssessmentSerializer, request)


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([HasRolePermission])
def speech_therapy_assessment(request):

    if request.method == 'GET':
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")

        items = SpeechTherapyAssessment.objects.filter(
            assessment_date__range=[from_date, to_date]
        ) if from_date and to_date else SpeechTherapyAssessment.objects.all()

        return Response(SpeechTherapyAssessmentSerializer(items, many=True).data)

    if request.method == 'POST':
        serializer = SpeechTherapyAssessmentSerializer(data=request.data)
        if serializer.is_valid():
            instance = save_with_audit(serializer, request)
            return Response(
                SpeechTherapyAssessmentSerializer(instance).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=400)

    if request.method == 'PUT':
        return update_assessment_record(SpeechTherapyAssessment, SpeechTherapyAssessmentSerializer, request)


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([HasRolePermission])
def physiotherapy_assessment(request):

    if request.method == 'GET':
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")

        items = PhysiotherapyAssessment.objects.filter(
            assessment_date__range=[from_date, to_date]
        ) if from_date and to_date else PhysiotherapyAssessment.objects.all()

        return Response(PhysiotherapyAssessmentSerializer(items, many=True).data)

    if request.method == 'POST':
        serializer = PhysiotherapyAssessmentSerializer(data=request.data)
        if serializer.is_valid():
            instance = save_with_audit(serializer, request)
            return Response(
                PhysiotherapyAssessmentSerializer(instance).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=400)

    if request.method == 'PUT':
        return update_assessment_record(PhysiotherapyAssessment, PhysiotherapyAssessmentSerializer, request)

@api_view(['GET', 'POST'])
@permission_classes([HasRolePermission])
def assessment_analysis_list_create(request):
    if request.method == "GET":
        records = AssessmentAnalysis.objects.all()
        serializer = AssessmentAnalysisSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == "POST":
        billing_no = request.data.get("billing_no")

        if not billing_no:
            return Response(
                {"billing_no": "billing_no is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ❌ Do NOT update if billing_no exists
        if AssessmentAnalysis.objects.filter(billing_no=billing_no).exists():
            return Response(
                {"error": "Assessment already exists for this billing_no"},
                status=status.HTTP_409_CONFLICT
            )

        # ✅ CREATE only
        serializer = AssessmentAnalysisSerializer(data=request.data)
        if serializer.is_valid():
            save_with_audit(serializer, request)  # created_by, created_date
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

 

@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([HasRolePermission])
def assessment_analysis_detail(request, pk):
    try:
        record = AssessmentAnalysis.objects.get(pk=pk)
    except AssessmentAnalysis.DoesNotExist:
        return Response(
            {"error": "Record not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "GET":
        serializer = AssessmentAnalysisSerializer(record)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method in ["PUT", "PATCH"]:
        serializer = AssessmentAnalysisSerializer(
            record,
            data=request.data,
            partial=(request.method == "PATCH")
        )

        if serializer.is_valid():
            update_with_audit(serializer, request)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
@permission_classes([HasRolePermission])
def behavioral_observation_options(request):
    if request.method == 'GET':
        if BehavioralObservationOption.objects.count() == 0:
            defaults = [
                "Binet Kamat Test of Intelligence (BKT)",
                "Vineland Social Maturity Scale (VSMS)",
                "Developmental Screening Test (DST)",
                "Childhood Autism Rating Scale - Second Edition (CARS-2)",
                "Modified Checklist for Autism in Toddlers (M-CHAT)",
                "ISAA (Indian Scale for Assessment of Autism)",
                "Seguin Form Board Test (SFBT)",
                "ADHD Assessment"
            ]
            for name in defaults:
                BehavioralObservationOption.objects.get_or_create(name=name)

        options = BehavioralObservationOption.objects.all().order_by('name')
        serializer = BehavioralObservationOptionSerializer(options, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        serializer = BehavioralObservationOptionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
