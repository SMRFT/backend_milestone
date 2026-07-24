from ..serializers import RegistrationSerializer
from ..models import Registration, PatientAssessment
from rest_framework.response import Response
from datetime import datetime ,timedelta ,date
from rest_framework.decorators import api_view , permission_classes
from rest_framework import status
from milestone_backend.models import PatientAttendance
from milestone_backend.serializers import PatientAttendanceSerializer
from django.db.models import Max
from django.http import JsonResponse
from ..models import Registration
from pyauth.auth import HasRolePermission
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.shortcuts import get_object_or_404
from pymongo import DESCENDING, MongoClient
import gridfs
import os
import certifi
from bson import ObjectId
from dotenv import load_dotenv
import calendar
from bson.decimal128 import Decimal128
from decimal import Decimal, InvalidOperation

load_dotenv()  # Load from .env if present

env_type = os.environ.get("ENV_CLASSIFICATION", "local")

mongo_uri = os.environ.get("GLOBAL_DB_HOST")
db_name = os.environ.get("MILESTONE_DB_NAME", "Milestone")

if env_type in ["test", "prod"]:
    client = MongoClient(mongo_uri)
else:
    client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())


from bson.decimal128 import Decimal128
from decimal import Decimal
import json

client = MongoClient(mongo_uri)
db = client["Milestone"]

def safe_float(value):
    """Convert MongoDB Decimal128, dict, Decimal, or other types safely to float."""
    if value is None:
        return 0.0

    if isinstance(value, Decimal128):
        return float(value.to_decimal())

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, dict) and "$numberDecimal" in value:
        try:
            return float(value["$numberDecimal"])
        except Exception:
            return 0.0

    try:
        return float(value)
    except Exception:
        return 0.0

def parse_bill_details(bill_details):
    if not bill_details:
        return []

    if isinstance(bill_details, list):
        return bill_details

    if isinstance(bill_details, str):
        try:
            return json.loads(bill_details)
        except:
            return []

    return []
def safe_parse_json(value):
    if not isinstance(value, str):
        return value
    
    # 1. Try standard JSON parsing
    try:
        parsed = json.loads(value)
        if isinstance(parsed, str):
            return safe_parse_json(parsed)
        return parsed
    except (ValueError, TypeError):
        pass

    # 2. Try handling Python representation strings (e.g. OrderedDict, python dicts/lists)
    if 'OrderedDict' in value or 'dict' in value or '(' in value or '[' in value:
        from collections import OrderedDict
        try:
            safe_ns = {
                'OrderedDict': OrderedDict,
                'dict': dict,
                'list': list,
                'tuple': tuple
            }
            parsed = eval(value, {"__builtins__": None}, safe_ns)
            
            def convert_to_json_types(obj):
                if isinstance(obj, OrderedDict) or isinstance(obj, dict):
                    return {k: convert_to_json_types(v) for k, v in obj.items()}
                elif isinstance(obj, list) or isinstance(obj, tuple):
                    return [convert_to_json_types(i) for i in obj]
                else:
                    return obj
            
            return convert_to_json_types(parsed)
        except Exception:
            pass

    # 3. Fallback: try converting python single quote representation to valid JSON
    try:
        repr_val = value.replace("'", '"')
        repr_val = repr_val.replace(': True', ': true').replace(': False', ': false').replace(': None', ': null')
        repr_val = repr_val.replace(', True', ', true').replace(', False', ', false').replace(', None', ', null')
        repr_val = repr_val.replace('[True', '[true').replace('[False', '[false').replace('[None', '[null')
        parsed = json.loads(repr_val)
        if isinstance(parsed, str):
            return safe_parse_json(parsed)
        return parsed
    except (ValueError, TypeError):
        pass

    return value

def clean_mongo_object(obj):
    """Recursively convert MongoDB types (Decimal128, ObjectId, datetime) into JSON-safe values, parsing specific JSON fields."""
    if isinstance(obj, Decimal128):
        return float(obj.to_decimal())
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime) or isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, list):
        return [clean_mongo_object(i) for i in obj]
    elif isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            if k in ['age', 'reason_for_visit', 'source_of_referral', 'assessments']:
                cleaned[k] = safe_parse_json(v)
            else:
                cleaned[k] = clean_mongo_object(v)
        return cleaned
    else:
        return obj

@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_all_attendance_patients(request):
    try:
        registration_col = db["milestone_backend_registration"]
        attendance_col = db["milestone_backend_patientattendance"]
        billing_col = db["milestone_backend_therapybilling"]

        # --------- MONTH FILTER ----------
        month = request.GET.get("month")
        date_filter = {}

        if month:
            try:
                year, mon = map(int, month.split("-"))
                start_date = datetime(year, mon, 1)
                end_date = start_date + relativedelta(months=1)

                date_filter = {
                    "attendance_date": {
                        "$gte": start_date,
                        "$lt": end_date
                    }
                }
            except:
                return Response(
                    {"status": "error", "message": "Invalid month format. Use YYYY-MM."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        query = {"is_active": True}

        if date_filter:
            query["attendance_date"] = date_filter["attendance_date"]

        attendances = list(attendance_col.find(query))

        attendance_map = {}

        for att in attendances:
            reg_no = att.get("registration_number")
            if not reg_no:
                continue

            if not att.get("is_approved", True):
                continue

            # Parse JSON therapy_details
            therapy_details = att.get("therapy_details", [])
            if isinstance(therapy_details, str):
                try:
                    therapy_details = json.loads(therapy_details)
                except:
                    therapy_details = []

            bill_nos = parse_bill_details(att.get("bill_details"))

            # Fetch bills
            bills = []
            if bill_nos:
                bills_cursor = billing_col.find(
                    {"billing_no": {"$in": bill_nos}},
                    {"_id": 0}
                )

                for bill in bills_cursor:
                    bills.append({
                        **bill,
                        "total_amount": safe_float(bill.get("total_amount")),
                        "total_amount_paid": safe_float(bill.get("total_amount_paid")),
                        "amount_paid": safe_float(bill.get("amount_paid")),
                        "bill_date": bill.get("bill_date").strftime("%Y-%m-%d")
                            if isinstance(bill.get("bill_date"), datetime)
                            else bill.get("bill_date"),
                        "attendance_date": bill.get("attendance_date").strftime("%Y-%m-%d")
                            if isinstance(bill.get("attendance_date"), datetime)
                            else bill.get("attendance_date"),
                        "created_date": bill.get("created_date").strftime("%Y-%m-%d %H:%M:%S")
                            if isinstance(bill.get("created_date"), datetime)
                            else bill.get("created_date"),
                    })

            attendance_info = {
                "_id": str(att.get("_id")),

                "registration_number": reg_no,

                "attendance_date": att.get("attendance_date").strftime("%Y-%m-%d")
                    if isinstance(att.get("attendance_date"), datetime)
                    else str(att.get("attendance_date")),

                "therapy_details": therapy_details,
                "therapy_charge": safe_float(att.get("therapy_charge")),
                "discount": safe_float(att.get("discount")),
                "discount_remarks": att.get("discount_remarks", ""),
                "session":att.get("session",0),
                "not_attending": safe_float(att.get("not_attending", 0)),
                "not_attending_remarks": att.get("not_attending_remarks", ""),

                "extra_attending": safe_float(att.get("extra_attending", 0)),
                "extra_attending_remarks": att.get("extra_attending_remarks", ""),

                "total_amount": safe_float(att.get("total_amount")),
                "total_amount_paid": safe_float(att.get("total_amount_paid")),

                "bill_details": bill_nos,   # 🔥 parsed list
                "bills": bills,             # 🔥 full bill objects
                "consultant_doctor": att.get("consultant_doctor"),

                "is_active": att.get("is_active", True),
                "is_approved": att.get("is_approved", False),

                "created_by": att.get("created_by"),
                "created_date": att.get("created_date").strftime("%Y-%m-%d %H:%M:%S")
                    if isinstance(att.get("created_date"), datetime)
                    else att.get("created_date"),

                "lastmodified_by": att.get("lastmodified_by"),
                "lastmodified_date": att.get("lastmodified_date").strftime("%Y-%m-%d %H:%M:%S")
                    if isinstance(att.get("lastmodified_date"), datetime)
                    else att.get("lastmodified_date"),
            }

            attendance_map.setdefault(reg_no, []).append(attendance_info)

        registrations = list(registration_col.find({}, {"_id": 0}))
        response_data = []

        for patient in registrations:
            reg_no = patient.get("registration_number")
            patient_att = attendance_map.get(reg_no, [])

            if month and not patient_att:
                continue

            total_charge = sum(a["therapy_charge"] for a in patient_att)

            response_data.append({
                **clean_mongo_object(patient),
                "attendances": patient_att,
                "total_therapy_charge": total_charge,
                "total_sessions": len(patient_att),
            })

        return Response(response_data, status=200 )

    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=500)

import re

def get_month_session_attendance_total(registration_number, target_year, target_month):
    if not registration_number:
        return 0, {}, {}

    clean_reg = str(registration_number).strip()
    if not clean_reg:
        return 0, {}, {}

    db_handle = client[db_name]
    psa_collection = db_handle['milestone_backend_patientsessionattendance']

    query = {
        "$and": [
            {
                "$or": [
                    {"registration_number": clean_reg},
                    {"registration_number": {"$regex": f"^{re.escape(clean_reg)}$", "$options": "i"}}
                ]
            },
            {
                "$or": [
                    {"is_active": True},
                    {"is_active": {"$exists": False}}
                ]
            }
        ]
    }

    records = list(psa_collection.find(query))

    total_sessions = 0
    counts_by_name = {}
    counts_by_id = {}

    for r in records:
        att_date = r.get("attendance_date")
        rec_year, rec_month = None, None

        if isinstance(att_date, datetime):
            rec_year, rec_month = att_date.year, att_date.month
        elif isinstance(att_date, date):
            rec_year, rec_month = att_date.year, att_date.month
        elif isinstance(att_date, str):
            try:
                parsed_dt = datetime.strptime(att_date[:10], '%Y-%m-%d')
                rec_year, rec_month = parsed_dt.year, parsed_dt.month
            except:
                continue

        if rec_year == target_year and rec_month == target_month:
            sess = int(r.get("sessions_attended") or 1)
            total_sessions += sess

            tname = r.get("therapy_name")
            tid = r.get("therapy_id")
            if tname:
                counts_by_name[tname] = counts_by_name.get(tname, 0) + sess
            if tid:
                counts_by_id[tid] = counts_by_id.get(tid, 0) + sess

    return total_sessions, counts_by_name, counts_by_id


@api_view(['POST'])
@permission_classes([HasRolePermission])
def add_patient_attendance(request):
    employee_id = request.data.get('auth-user-id')
    registration_number = request.data.get('registration_number')
    attendance_date_str = request.data.get('attendance_date')
    therapy_details = request.data.get('therapy_details', [])
    discount = float(request.data.get('discount', 0))
    session = request.data.get("session",0)
    # --- Required Fields Check ---
    if not registration_number or not attendance_date_str:
        return Response(
            {"error": "registration_number and attendance_date are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # --- Parse Date ---
    try:
        attendance_date = datetime.fromisoformat(attendance_date_str).date()
    except ValueError:
        return Response(
            {"error": "Invalid attendance_date format. Use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ================================
    #          MONTH CHECK
    # ================================
    first_day = attendance_date.replace(day=1)

    if attendance_date.month == 12:
        last_day = attendance_date.replace(
            year=attendance_date.year + 1,
            month=1,
            day=1
        ) - timedelta(seconds=1)
    else:
        last_day = attendance_date.replace(
            month=attendance_date.month + 1,
            day=1
        ) - timedelta(seconds=1)

    existing_month_attendance = PatientAttendance.objects.filter(
        registration_number=registration_number,
        attendance_date__gte=first_day,
        attendance_date__lte=last_day,
        is_active=True
    ).first()

    if existing_month_attendance:
        return Response(
            {"error": "Attendance already exists for this patient in this month."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ================================
    #        SAME DAY CHECK
    # ================================
    if PatientAttendance.objects.filter(
        registration_number=registration_number,
        attendance_date=attendance_date,
        is_active=True
    ).exists():
        return Response(
            {"error": "Attendance already exists for this date."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ================================
    #   SESSION ATTENDANCE MINIMUM CHECK
    # ================================
    total_logged_sessions, _, _ = get_month_session_attendance_total(
        registration_number, attendance_date.year, attendance_date.month
    )

    submitted_total_sessions = sum(
        int(t.get("sesion_per_therapy") or t.get("sessions_per_month") or 0)
        for t in therapy_details
        if isinstance(t, dict)
    )
    if not submitted_total_sessions and session:
        try:
            submitted_total_sessions = int(session)
        except:
            submitted_total_sessions = 0

    if total_logged_sessions > 0 and submitted_total_sessions < total_logged_sessions:
        return Response(
            {"error": f"A total of {total_logged_sessions} session(s) have already been logged in Session Attendance for this month. Total monthly sessions must be at least {total_logged_sessions}."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # --- Calculate Total Therapy Charge ---
    total_charge = sum(
        float(t.get("therapy_charge", 0))
        for t in therapy_details
        if isinstance(t, dict)
    )

    # --- Store simplified therapy details ---
    simplified_details = [
        {
            "therapy_name": t.get("therapy_name"),
            "therapy_type": t.get("therapy_type"),
            "sesion_per_therapy":t.get("sesion_per_therapy"),
            "therapy_charge":t.get("therapy_charge"),
            "discount":t.get("discount")
        }
        for t in therapy_details if isinstance(t, dict)
    ]

    # --- Prepare data ---
    data = request.data.copy()
    data["total_amount"] = total_charge - discount
    data["therapy_charge"] = total_charge
    data["therapy_details"] = simplified_details
    data["discount"] = discount
    data["is_approved"] = False
    data["session"] = session

    serializer = PatientAttendanceSerializer(data=data)

    if serializer.is_valid():
        instance = serializer.save(
            created_by=employee_id,
            lastmodified_by=employee_id,
            lastmodified_date=datetime.now()
        )
        return Response(PatientAttendanceSerializer(instance).data, status=201)

    return Response(serializer.errors, status=400)

# --- Global Configuration ---
MONGO_URI = os.environ.get("GLOBAL_DB_HOST")
DB_NAME = os.environ.get("MILESTONE_DB_NAME", "Milestone")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

attendance_col = db["milestone_backend_patientattendance"]
registration_col = db["milestone_backend_registration"]

# clean_mongo_object is defined at the top of this file

@api_view(['GET'])
@permission_classes([HasRolePermission])  # remove permission temporarily for testing
def get_all_patient_attendance(request):
    """
    ✅ Mobile Optimized: Returns patient attendance records filtered by month.
    ✅ Defaults to CURRENT month if no params provided.
    ✅ Query Params: ?month=10&year=2023
    """
    try:
        # 1. Determine Date Range
        today = datetime.now()
        
        # Get query params or default to current date
        try:
            req_month = int(request.query_params.get("month", today.month))
            req_year = int(request.query_params.get("year", today.year))
        except ValueError:
            return Response({"status": "error", "message": "Invalid year or month format"}, status=400)

        # Calculate start and end of the month for MongoDB Query
        _, last_day_of_month = calendar.monthrange(req_year, req_month)
        
        start_date = datetime(req_year, req_month, 1, 0, 0, 0)
        end_date = datetime(req_year, req_month, last_day_of_month, 23, 59, 59)

        # 2. Fetch Attendance (Filtered by Date Range)
        # ✅ FIXED: Changed "date" to "attendance_date" to match your DB schema
        query = {
            "attendance_date": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        
        # Sort by attendance_date descending
        attendances = list(attendance_col.find(query).sort("attendance_date", -1))

        if not attendances:
            return Response({
                "status": "success",
                "message": "No records found for this month",
                "filter": f"{req_month}-{req_year}",
                "count": 0,
                "data": []
            }, status=status.HTTP_200_OK)

        # 3. Optimized Join (Only fetch relevant registrations)
        unique_reg_numbers = list(set(
            a.get("registration_number") for a in attendances if a.get("registration_number")
        ))

        registrations = {
            r.get("registration_number"): clean_mongo_object(r)
            for r in registration_col.find({"registration_number": {"$in": unique_reg_numbers}})
        }

        # 4. Combine Data
        combined_data = []
        for a in attendances:
            reg_data = registrations.get(a.get("registration_number"), {})
            a_clean = clean_mongo_object(a)

            combined_data.append({
                **reg_data,
                **a_clean
            })

        safe_data = clean_mongo_object(combined_data)

        return Response({
            "status": "success",
            "filter": f"{req_month}-{req_year}",
            "count": len(safe_data),
            "data": safe_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
def get_therapy_details(request):
    try:
        # --- MongoDB Connection ---
        client = MongoClient(mongo_uri)
        db = client[db_name]  # ✅ Correct: use db_name string to get DB object
        therapy_col = db["milestone_backend_therapydetails"]

        # --- Fetch all documents ---
        therapies = list(therapy_col.find({}, {"_id": 0}))  # exclude _id for cleaner output

        # --- Sort by created_date (optional) ---
        therapies.sort(key=lambda x: x.get("created_date", datetime.min), reverse=True)

        return Response({
            "status": "success",
            "count": len(therapies),
            "data": therapies
        })

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=500)

    
db = client["Milestone"]

def safe_float(value):
    """Convert MongoDB Decimal128, dict, Decimal, or other types safely to float."""
    if value is None:
        return 0.0

    if isinstance(value, Decimal128):
        return float(value.to_decimal())

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, dict) and "$numberDecimal" in value:
        try:
            return float(value["$numberDecimal"])
        except Exception:
            return 0.0

    try:
        return float(value)
    except Exception:
        return 0.0

@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_pending_attendance_requests(request):
    """
    Fetch all pending attendance entries (is_approved=False)
    Includes:
    - Patient registration data
    - Parsed therapy details
    - Parsed consultant doctors
    - Discount, total amount, extra/not attending info
    """
    try:
        registration_col = db["milestone_backend_registration"]
        attendance_col = db["milestone_backend_patientattendance"]

        # --- Fetch pending attendance ---
        pending_attendances = list(attendance_col.find({
            "is_active": True,
            "is_approved": False
        }))

        # --- Fetch registrations ---
        registrations = list(registration_col.find({}, {"_id": 0}))
        registration_map = {
            reg.get("registration_number"): clean_mongo_object(reg) for reg in registrations
        }

        response_data = []

        for att in pending_attendances:
            reg_no = att.get("registration_number")
            if not reg_no:
                continue

            patient_info = registration_map.get(reg_no, {})

            # Parse list-like fields
            def parse_json_field(val):
                if isinstance(val, list):
                    return val
                if isinstance(val, str):
                    try:
                        return json.loads(val)
                    except:
                        return []
                return []

            therapy_details = parse_json_field(att.get("therapy_details"))
            consultant_doctor = parse_json_field(att.get("consultant_doctor"))
            not_attending_details = parse_json_field(att.get("not_attending_details"))
            extra_attending_details = parse_json_field(att.get("extra_attending_details"))
            bill_details = parse_json_field(att.get("bill_details"))

            attendance_info = {
                "_id": str(att.get("_id")),
                "registration_number": reg_no,

                "attendance_date": (
                    att.get("attendance_date").strftime("%Y-%m-%d")
                    if isinstance(att.get("attendance_date"), datetime)
                    else str(att.get("attendance_date"))
                ),

                "session": att.get("session"),

                # Main charges
                "therapy_charge": safe_float(att.get("therapy_charge")),
                "discount": safe_float(att.get("discount")),
                "discount_remarks": att.get("discount_remarks", ""),

                # Not attending
                "not_attending": safe_float(att.get("not_attending")),
                "not_attending_details": not_attending_details,
                "not_attending_remarks": att.get("not_attending_remarks", ""),

                # Extra attending
                "extra_attending": safe_float(att.get("extra_attending")),
                "extra_attending_details": extra_attending_details,
                "extra_attending_remarks": att.get("extra_attending_remarks", ""),

                # Totals
                "total_amount": safe_float(att.get("total_amount")),
                "total_amount_paid": safe_float(att.get("total_amount_paid")),
                "bill_details": bill_details,

                # Therapy & doctor
                "therapy_details": therapy_details,
                "consultant_doctor": consultant_doctor,

                "is_approved": att.get("is_approved", False),
            }

            response_data.append({
                **patient_info,
                "attendance": attendance_info
            })

        return Response({
            "status": "success",
            "count": len(response_data),
            "data": response_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

db = client["Milestone"]

# clean_mongo_object is defined at the top of this file
    
@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_patient_month_session_counts(request):
    try:
        registration_number = request.GET.get('registration_number', '')
        date_str = request.GET.get('attendance_date') or request.GET.get('date')
        
        if not registration_number or not date_str:
            return Response(
                {"error": "registration_number and date/attendance_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        total_logged_sessions, counts_by_name, counts_by_id = get_month_session_attendance_total(
            registration_number, date_obj.year, date_obj.month
        )
        
        return Response({
            "status": "success",
            "total_logged_sessions": total_logged_sessions,
            "counts_by_id": counts_by_id,
            "counts_by_name": counts_by_name
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["PATCH"])
@permission_classes([HasRolePermission])
def update_attendance_by_reg_and_date(request):
    try:
        attendance_col = db["milestone_backend_patientattendance"]

        registration_number = request.data.get("registration_number")
        date_str = request.data.get("attendance_date")

        if not registration_number or not date_str:
            return Response({"status": "error", "message": "registration_number and attendance_date are required."}, status=400)

        # Parse date
        try:
            date_obj = datetime.fromisoformat(date_str)
        except ValueError:
            return Response({"status": "error", "message": "Invalid attendance_date format."}, status=400)

        # Find attendance record
        attendance = attendance_col.find_one({
            "registration_number": registration_number,
            "attendance_date": {
                "$gte": date_obj.replace(hour=0, minute=0, second=0),
                "$lte": date_obj.replace(hour=23, minute=59, second=59)
            },
            "is_active": True
        })

        if not attendance:
            return Response({"status": "error", "message": "Record not found."}, status=404)

        if "therapy_details" in request.data or "session" in request.data:
            total_logged, _, _ = get_month_session_attendance_total(
                registration_number, date_obj.year, date_obj.month
            )

            t_details_input = request.data.get("therapy_details", [])
            if isinstance(t_details_input, str):
                try:
                    t_details_list = json.loads(t_details_input)
                except:
                    t_details_list = []
            elif isinstance(t_details_input, list):
                t_details_list = t_details_input
            else:
                t_details_list = []

            submitted_total = sum(
                int(t.get("sesion_per_therapy") or t.get("sessions_per_month") or 0)
                for t in t_details_list
                if isinstance(t, dict)
            )
            if not submitted_total and "session" in request.data:
                try:
                    submitted_total = int(request.data["session"])
                except:
                    submitted_total = 0

            if total_logged > 0 and submitted_total < total_logged:
                return Response(
                    {"status": "error", "message": f"A total of {total_logged} session(s) have already been logged in Session Attendance for this month. Total monthly sessions must be at least {total_logged}."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 1. Define ALL fields you want to allow updating
        allowed_fields = [
            "session",
            "therapy_details", "therapy_charge",
            "discount", "discount_remarks",
            "not_attending", "not_attending_details", "not_attending_remarks",
            "extra_attending", "extra_attending_details", "extra_attending_remarks",
            "total_amount", "total_amount_paid",
            "is_approved", "is_active",
            "bill_details",
            "consultant_doctor"
        ]

        # 2. Define which of those fields MUST be treated as Lists/Arrays
        list_fields = [
            "therapy_details",
            "not_attending_details",
            "extra_attending_details",
            "bill_details",
            "consultant_doctor"
        ]

        # 3. Define Decimal fields
        decimal_fields = [
            "extra_attending", "not_attending", "discount", 
            "total_amount", "total_amount_paid", "therapy_charge"
        ]

        update_fields = {}

        # --- PROCESS INPUTS ---
        for field in allowed_fields:
            if field in request.data:
                value = request.data[field]

                # A. Handle Lists
                if field in list_fields:
                    if isinstance(value, list):
                        update_fields[field] = json.dumps(value)  # convert list → JSON string
                    else:
                        update_fields[field] = str(value)  # keep original string

                # B. Handle Decimals
                elif field in decimal_fields:
                    try:
                        update_fields[field] = Decimal128(str(value))
                    except:
                        pass

                # C. Handle Booleans
                elif field in ["is_approved", "is_active"]:
                    update_fields[field] = str(value).lower() == 'true' if isinstance(value, str) else bool(value)

                # D. Handle Strings
                else:
                    update_fields[field] = value

        # --- UPDATE MONGODB (OUTSIDE THE LOOP) ---
        if not update_fields:
            return Response({"status": "error", "message": "No valid fields to update."}, status=400)

        update_fields["lastmodified_by"] = request.data.get("auth-user-id", "system")
        update_fields["lastmodified_date"] = datetime.now()

        attendance_col.update_one(
            {"_id": attendance["_id"]},
            {"$set": update_fields}
        )

        # Retrieve and Clean for Response
        updated = attendance_col.find_one({"_id": attendance["_id"]})
        updated = clean_mongo_object(updated)

        return Response({
            "status": "success",
            "message": "Attendance updated successfully.",
            "updated_data": updated
        }, status=200)

    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=500)

def safe_decimal(value):
    """Convert value to Decimal128 safely."""
    if value in [None, "", " ", "null", "undefined"]:
        return Decimal128("0")   # default or skip
    try:
        return Decimal128(str(Decimal(str(value))))
    except InvalidOperation:
        raise ValueError(f"Invalid decimal value: {value}")

def to_float(value):
    """Convert Decimal128, Decimal, int, float, or string to float."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal128):
        return float(value.to_decimal())
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except:
        return 0.0

@api_view(["PATCH"])
@permission_classes([HasRolePermission])
def update_attendance_sessions(request):

    attendance_col = db["milestone_backend_patientattendance"]

    try:
        registration_number = request.data.get("registration_number")
        date_str = request.data.get("attendance_date")

        if not registration_number or not date_str:
            return Response({
                "status": "error",
                "message": "registration_number and attendance_date are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Parse date
        try:
            date_obj = datetime.fromisoformat(date_str)
        except:
            return Response({
                "status": "error",
                "message": "Invalid attendance_date format. Use YYYY-MM-DD."
            }, status=400)

        # Find the record
        attendance = attendance_col.find_one({
            "registration_number": registration_number,
            "attendance_date": {
                "$gte": date_obj.replace(hour=0, minute=0, second=0),
                "$lte": date_obj.replace(hour=23, minute=59, second=59)
            },
            "is_active": True
        })

        if not attendance:
            return Response({
                "status": "error",
                "message": "Attendance not found."
            }, status=404)

        # Allowed fields including JSON strings
        allowed_fields = [
            "discount",
            "discount_remarks",

            "not_attending",
            "not_attending_details",
            "not_attending_remarks",

            "extra_attending",
            "extra_attending_details",
            "extra_attending_remarks",

            "total_amount",
            "total_amount_paid",

            "is_active"
        ]
    
        update_fields = {}

        for field in allowed_fields:
            if field not in request.data:
                continue

            value = request.data[field]

            # Decimal fields
            if field in ["discount", "total_amount", "total_amount_paid",
                        "not_attending", "extra_attending"]:
                update_fields[field] = safe_decimal(value)

            # JSON list fields
            elif field in ["not_attending_details", "extra_attending_details"]:
                update_fields[field] = json.dumps(value)

            # Plain text / boolean fields
            else:
                update_fields[field] = value

        # --- Recalculate total_amount dynamically ---
        original_total = to_float(attendance.get("therapy_charge", 0))

        not_att = to_float(update_fields.get("not_attending", attendance.get("not_attending", 0)))
        extra_att = to_float(update_fields.get("extra_attending", attendance.get("extra_attending", 0)))

        new_total = original_total - not_att + extra_att

        update_fields["total_amount"] = Decimal128(str(new_total))

        # Always force approval reset
        update_fields["is_approved"] = False

        # Extra meta fields
        update_fields["lastmodified_by"] = request.data.get("auth-user-id", "system")
        update_fields["lastmodified_date"] = datetime.now()

        attendance_col.update_one({"_id": attendance["_id"]}, {"$set": update_fields})

        updated = attendance_col.find_one({"_id": attendance["_id"]})
        updated = clean_mongo_object(updated)

        return Response({
            "status": "success",
            "message": "Attendance updated successfully.",
            "updated_data": updated
        })

    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=500)

from datetime import datetime
import json

@api_view(["GET"])
@permission_classes([HasRolePermission])
def get_all_patient_oldattendance(request):
    month = request.query_params.get("month")
    year = request.query_params.get("year")

    # Validate month and year
    if not month or not year:
        return Response({
            "status": "error",
            "message": "month and year are required"
        }, status=400)

    try:
        month = int(month)
        year = int(year)
    except:
        return Response({
            "status": "error",
            "message": "month and year must be integers"
        }, status=400)

    oldattendance_col = db["milestone_backend_patientoldattendance"]
    registration_col = db["milestone_backend_registration"]

    # 1️⃣ Prepare Month Filter
    start_date = datetime(year, month, 1)
    end_month = month + 1 if month < 12 else 1
    end_year = year if month < 12 else year + 1
    end_date = datetime(end_year, end_month, 1)

    month_filter = {
        "date": {
            "$gte": start_date,
            "$lt": end_date
        }
    }

    # 2️⃣ Get all old attendance for the month
    attendance_data = list(oldattendance_col.find(month_filter))

    if not attendance_data:
        return Response({
            "status": "success",
            "count": 0,
            "data": [],
            "message": "No attendance found for this month"
        })

    # 3️⃣ Extract all unique registration numbers
    reg_numbers = list({item["registration_number"] for item in attendance_data})

    # 4️⃣ Fetch all matching child details
    registration_details = list(
        registration_col.find({"registration_number": {"$in": reg_numbers}})
    )

    # Convert registration data to dictionary {reg_no: details}
    reg_map = {i["registration_number"]: clean_mongo_object(i) for i in registration_details}

    # 5️⃣ Build the final combined response
    final_output = []

    for item in attendance_data:
        att = clean_mongo_object(item)

        # Convert therapy_details from string to JSON
        if isinstance(att.get("therapy_details"), str):
            try:
                att["therapy_details"] = json.loads(att["therapy_details"])
            except:
                pass

        reg_no = att["registration_number"]
        child_details = reg_map.get(reg_no, {})

        final_output.append({
            "registration_number": reg_no,
            "child_details": child_details,
            "attendance_details": att
        })

    return Response({
        "status": "success",
        "count": len(final_output),
        "data": final_output
    })
