from datetime import datetime
import json
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.decorators import api_view , permission_classes
from rest_framework.response import Response
from datetime import datetime, timezone, timedelta
from ..models import OthersBilling
from ..serializers import OthersBillingSerializer
from ..models import TherapyBilling
from ..serializers import TherapyBillingSerializer
from pyauth.auth import HasRolePermission
from pymongo import DESCENDING, MongoClient
import gridfs
import os
import certifi
from dotenv import load_dotenv
from rest_framework import status

@csrf_exempt
@api_view(['POST'])
@permission_classes([HasRolePermission])
def therapy_billing(request):
    from .invoice import get_latest_billing_no  # Move import inside function
    
    # Extract employee ID from request
    employee_id = request.data.get('auth-user-id')
    
    # Pass employee_id through context
    serializer = TherapyBillingSerializer(data=request.data, context={'employee_id': employee_id})
    
    if serializer.is_valid():
        # Get billing number if not provided
        billing_no = serializer.validated_data.get('billing_no')
        if not billing_no:
            latest_billing_response = get_latest_billing_no(None)
            latest_billing_data = json.loads(latest_billing_response.content.decode())
            billing_no = latest_billing_data.get('billing_no', '001')
        
        # Save with additional fields
        therapy_billing_instance = serializer.save(
            created_by=employee_id,
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            billing_no=billing_no
        )
        
        return Response(TherapyBillingSerializer(therapy_billing_instance).data, status=201)

    return Response(serializer.errors, status=400)




@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_therapy_reports(request):
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')

    # Convert date strings to UTC-aware datetime objects
    if from_date_str:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)
    else:
        from_date = None

    if to_date_str:
        # Use `<` instead of `<=` to ensure we capture the full day
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc) + timedelta(seconds=1)
    else:
        to_date = None

    # Query with proper filters
    if from_date and to_date:
        therapy_billing_data = TherapyBilling.objects.filter(date__gte=from_date, date__lt=to_date)  # Use `lt` instead of `lte`
    elif from_date:
        therapy_billing_data = TherapyBilling.objects.filter(date__gte=from_date)
    elif to_date:
        therapy_billing_data = TherapyBilling.objects.filter(date__lt=to_date)
    else:
        therapy_billing_data = TherapyBilling.objects.all()

    # Serialize and return data
    serializer = TherapyBillingSerializer(therapy_billing_data, many=True)
    return Response(serializer.data)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from datetime import datetime
from bson.decimal128 import Decimal128
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from pymongo import MongoClient
import os, json

@api_view(['GET'])
@permission_classes([HasRolePermission])
def pending_payment_report(request):
    try:
        # --- MongoDB Connection ---
        mongo_uri = os.environ.get("GLOBAL_DB_HOST")
        client = MongoClient(mongo_uri)
        db = client["Milestone"]

        attendance_col = db['milestone_backend_patientattendance']
        billing_col = db['milestone_backend_therapybilling']
        registration_col = db['milestone_backend_registration']

        # --- Helper: Safe Float Converter ---
        def safe_float(value):
            """Convert MongoDB Decimal128, Decimal, or any numeric safely to float."""
            try:
                if isinstance(value, Decimal128):
                    return float(value.to_decimal())
                if isinstance(value, Decimal):
                    return float(value)
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str):
                    return float(value.strip())
            except Exception:
                return 0.0
            return 0.0

        # --- Helper: Calculate Age ---
        def calculate_age(dob):
            if not dob:
                return {"year": 0, "months": 0, "days": 0}
            today = datetime.today()
            delta = relativedelta(today, dob)
            return {"year": delta.years, "months": delta.months, "days": delta.days}

        final_output = []

        # --- Get all active attendances ---
        active_attendances = list(attendance_col.find({"is_active": True}))

        for att in active_attendances:
            reg_no = att.get("registration_number")
            if not reg_no:
                continue

            # --- Attendance date ---
            att_date = att.get("date") or att.get("attendance_date")
            if isinstance(att_date, datetime):
                att_date_str = att_date.strftime("%Y-%m-%dT00:00:00Z")
            else:
                att_date_str = str(att_date)

            therapy_charge = safe_float(att.get("therapy_charge", 0))

            # --- Registration details ---
            reg = registration_col.find_one({"registration_number": reg_no})
            if not reg:
                continue

            name = reg.get("name_of_child")
            gender = reg.get("sex")
            dob = reg.get("dob")

            if isinstance(dob, str):
                try:
                    dob_obj = datetime.strptime(dob[:10], "%Y-%m-%d")
                except:
                    dob_obj = None
            else:
                dob_obj = dob

            age = calculate_age(dob_obj) if dob_obj else {"year": 0, "months": 0, "days": 0}

            # --- Find matching bills for same reg_no ---
            bills = list(billing_col.find({
                "registration_number": reg_no,
                "attendance_date": {"$exists": True}
            }))

            matched_bills = []
            total_pending = 0
            fully_paid_session = False

            for b in bills:
                b_att_date = b.get("attendance_date")

                if isinstance(b_att_date, dict) and "$date" in b_att_date:
                    b_att_date = datetime.fromisoformat(
                        b_att_date["$date"].replace("Z", "+00:00")
                    ).strftime("%Y-%m-%dT00:00:00Z")
                elif isinstance(b_att_date, datetime):
                    b_att_date = b_att_date.strftime("%Y-%m-%dT00:00:00Z")
                else:
                    b_att_date = str(b_att_date)

                # --- Match exact attendance date ---
                if b_att_date != att_date_str:
                    continue

                # --- Parse remaining_amount safely ---
                remaining_raw = b.get("remaining_amount", {})
                if isinstance(remaining_raw, str):
                    try:
                        remaining_data = json.loads(remaining_raw.replace("'", '"'))
                    except:
                        remaining_data = {}
                elif isinstance(remaining_raw, dict):
                    remaining_data = remaining_raw
                else:
                    remaining_data = {}

                remaining_value = safe_float(remaining_data.get("value", 0))
                status = remaining_data.get("status", "Pending")

                # --- Skip if fully paid ---
                if remaining_value <= 0:
                    fully_paid_session = True
                    break

                total_pending += remaining_value

                matched_bills.append({
                    "billing_no": b.get("billing_no"),
                    "therapy_charge": safe_float(b.get("therapy_charge", 0)),
                    "amount_paid": safe_float(b.get("amount_paid", 0)),
                    "remaining_value": remaining_value,
                    "status": status,
                    "paid_date": b.get("date"),
                    "new_bill_no": remaining_data.get("new_bill_no"),
                    "attendance_date": att_date_str
                })

            # --- Exclude fully paid sessions ---
            if fully_paid_session:
                continue

            # --- Unbilled sessions ---
            if not matched_bills:
                final_output.append({
                    "registration_number": reg_no,
                    "name": name,
                    "gender": gender,
                    "dob": dob,
                    "age": age,
                    "attendance_dates": [att_date_str],
                    "therapy_charge": therapy_charge,
                    "amount_pending": therapy_charge,
                    "date": att_date_str,
                    "bills": [],
                    "status": "Unbilled"
                })
                continue

            # --- Partial payment sessions ---
            final_output.append({
                "registration_number": reg_no,
                "name": name,
                "gender": gender,
                "dob": dob,
                "age": age,
                "attendance_dates": [att_date_str],
                "therapy_charge": therapy_charge,
                "amount_pending": total_pending,
                "date": att_date_str,
                "bills": matched_bills,
                "status": "Partially Paid"
            })

        return Response(final_output)

    except Exception as e:
        return Response({"error": str(e)}, status=500)
