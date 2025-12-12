from datetime import datetime
import json
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.decorators import api_view , permission_classes
from rest_framework.response import Response
from datetime import datetime, timezone, timedelta
from ..models import OthersBilling
from ..serializers import OthersBillingSerializer
from ..models import TherapyBilling, PatientAttendance
from ..serializers import TherapyBillingSerializer
from pyauth.auth import HasRolePermission
from pymongo import DESCENDING, MongoClient
import gridfs
import os
import certifi
from dotenv import load_dotenv
from rest_framework import status
from decimal import Decimal
from bson.decimal128 import Decimal128
from datetime import datetime, date

mongo_uri = os.environ.get("GLOBAL_DB_HOST")
db_name = os.environ.get("MILESTONE_DB_NAME", "Milestone")

# Connect to MongoDB
client = MongoClient(mongo_uri)
db = client[db_name]
attendance_col = db["milestone_backend_patientattendance"]

def clean_decimal(value):
    if isinstance(value, Decimal128):
        return value.to_decimal()
    return Decimal(value)

@csrf_exempt
@api_view(['POST'])
@permission_classes([HasRolePermission])
def therapy_billing(request):
    from .invoice import get_latest_billing_no

    employee_id = request.data.get('auth-user-id')

    serializer = TherapyBillingSerializer(data=request.data, context={'employee_id': employee_id})

    if serializer.is_valid():

        # Generate billing no
        billing_no = serializer.validated_data.get('billing_no')
        if not billing_no:
            latest_billing_response = get_latest_billing_no(None)
            billing_no = json.loads(latest_billing_response.content.decode()).get("billing_no", "001")

        # Save Billing
        therapy_billing_instance = serializer.save(
            created_by=employee_id,
            bill_date=datetime.now().date(),
            billing_no=billing_no
        )

        # -----------------------------------------------------------
        # DIRECT MONGO UPDATE (NO DJONGO ORM)
        # -----------------------------------------------------------
        reg_no = serializer.validated_data.get('registration_number')
        attendance_date = serializer.validated_data.get('attendance_date')
        amount_paid = serializer.validated_data.get('amount_paid', 0)

        # Convert attendance_date to datetime.date
        if isinstance(attendance_date, str):
            attendance_date_obj = datetime.strptime(attendance_date, "%Y-%m-%d")
        else:
            attendance_date_obj = datetime.combine(attendance_date, datetime.min.time())

        # Find existing record using date range (avoids timezone mismatch)
        start = attendance_date_obj
        end = attendance_date_obj + timedelta(days=1)

        attendance_doc = attendance_col.find_one({
            "registration_number": reg_no,
            "attendance_date": {"$gte": start, "$lt": end}
        })

        if attendance_doc:

            # Convert Decimal128 → Decimal
            total_paid = clean_decimal(attendance_doc.get("total_amount_paid", 0))
            total_paid = total_paid + Decimal(amount_paid)

            # Update bill details array
            bill_list = attendance_doc.get("bill_details", "[]")
            if isinstance(bill_list, str):
                try:
                    bill_list = json.loads(bill_list)
                except:
                    bill_list = []
            bill_list.append(billing_no)

            # Perform direct mongo update
            attendance_col.update_one(
                {"_id": attendance_doc["_id"]},
                {
                    "$set": {
                        "total_amount_paid": Decimal128(str(total_paid)),
                        "bill_details": json.dumps(bill_list),
                        "lastmodified_by": employee_id,
                        "lastmodified_date": datetime.utcnow(),
                    }
                }
            )

        return Response(TherapyBillingSerializer(therapy_billing_instance).data, status=201)

    return Response(serializer.errors, status=400)

@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_therapy_reports(request):
    try:
        from_date_str = request.GET.get('from_date')
        to_date_str = request.GET.get('to_date')
        # Initialize filter dates
        from_date = None
        to_date = None
        # Convert date strings to UTC-aware datetime objects
        if from_date_str:
            try:
                from_date = datetime.strptime(from_date_str, '%Y-%m-%d').replace(
                    hour=0, minute=0, second=0, tzinfo=timezone.utc
                )
            except ValueError:
                return Response({"error": "Invalid from_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        if to_date_str:
            try:
                # Set time to end of day (23:59:59) + 1 second to cover the full day using 'lt'
                parsed_to_date = datetime.strptime(to_date_str, '%Y-%m-%d').replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
                to_date = parsed_to_date + timedelta(seconds=1)
            except ValueError:
                return Response({"error": "Invalid to_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        # Build the query filters
        # Using 'bill_date' because 'date' does not exist in the TherapyBilling model
        filters = {}
        if from_date:
            filters['bill_date__gte'] = from_date
        if to_date:
            filters['bill_date__lt'] = to_date
        # Apply filters
        therapy_billing_data = TherapyBilling.objects.filter(**filters).order_by('-bill_date')
        # Serialize and return data
        serializer = TherapyBillingSerializer(therapy_billing_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        # Log the error internally here if you have a logger
        print(f"Error in get_therapy_reports: {str(e)}")
        return Response(
            {"error": "An internal server error occurred processing the report."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

from django.db.models import F
from decimal import Decimal, InvalidOperation
from rest_framework.decorators import api_view
from rest_framework.response import Response

# import your models
from ..models import Registration, PatientAttendance, TherapyBilling

def safe_float(v):
    """Convert Decimal/str/None safely to float (fallback 0.0)."""
    if v is None:
        return 0.0
    if isinstance(v, float):
        return v
    try:
        return float(v)
    except (ValueError, TypeError, InvalidOperation):
        # Try Decimal then float
        try:
            return float(Decimal(str(v)))
        except Exception:
            return 0.0


@api_view(["GET"])
@permission_classes([HasRolePermission])
def pending_payment_report(request):
    """
    Djongo-safe: fetch all attendances, filter in Python:
      - is_active must be True
      - total_amount > total_amount_paid
    Also attach registration details and billing info.
    """

    # 1) Fetch all attendances (materialize into list to avoid lazy queries)
    try:
        all_attendance = list(PatientAttendance.objects.all())
    except Exception as e:
        # If QuerySet iteration itself fails, report clearly
        return Response({"status": "error", "message": f"DB fetch error: {e}"}, status=500)

    pending_list = []

    # 2) Filter in Python with safe numeric conversion and visible debug logs
    for a in all_attendance:
        try:
            amt = safe_float(a.total_amount)
            paid = safe_float(a.total_amount_paid)
            active = bool(a.is_active)

            # Debug line: shows each record's numeric values
            # print(f"Record: {a.registration_number} {amt} {paid} Active={active}")

            if active and (amt > paid):
                # print(f"PENDING -> {a.registration_number} (due {amt - paid})")
                pending_list.append(a)

        except Exception as e:
            # Don't hide errors — print them so you can inspect logs
            print(f"Error checking record {getattr(a,'registration_number', a)}: {e}")
            continue

    # 3) If nothing pending, return early (same shape as before)
    if not pending_list:
        return Response({
            "status": "success",
            "count": 0,
            "data": [],
            "message": "No pending attendance found."
        })

    # 4) Load registration details in one go
    reg_numbers = {a.registration_number for a in pending_list if a.registration_number}
    registrations = list(Registration.objects.filter(registration_number__in=list(reg_numbers)))
    reg_map = {
        r.registration_number: {
            "name_of_child": r.name_of_child,
            "dob": r.dob.isoformat() if r.dob else None,
            "age": r.age,
            "sex": r.sex,
            "mother_name": r.mother_name,
            "father_name": r.father_name,
            "mother_phone_number": r.mother_phone_number,
            "father_phone_number": r.father_phone_number,
            "address": r.address,
            "mail_id": r.mail_id,
            "registration_number": r.registration_number
        }
        for r in registrations
    }

    # 5) Build final result
    result = []
    for a in pending_list:
        amt = safe_float(a.total_amount)
        paid = safe_float(a.total_amount_paid)

        attendance_obj = {
            "attendance_id": getattr(a, "id", None),
            "registration_number": a.registration_number,
            "attendance_date": a.attendance_date.isoformat() if a.attendance_date else None,
            "session": a.session,
            "therapy_details": a.therapy_details,
            "therapy_charge": safe_float(a.therapy_charge),
            "discount": safe_float(a.discount),
            "not_attending": safe_float(a.not_attending),
            "extra_attending": safe_float(a.extra_attending),
            "total_amount": amt,
            "total_amount_paid": paid,
            "total_due": round(amt - paid, 2),
            "bill_details": a.bill_details,
        }

        # Billing info
        bills_info = []
        try:
            if a.bill_details:
                bills = list(TherapyBilling.objects.filter(billing_no__in=a.bill_details))
                bill_map = {b.billing_no: b for b in bills}
                for bno in a.bill_details:
                    b = bill_map.get(bno)
                    if b:
                        b_total = safe_float(b.total_amount)
                        b_paid = safe_float(b.total_amount_paid)
                        bills_info.append({
                            "billing_no": b.billing_no,
                            "bill_date": b.bill_date.isoformat() if b.bill_date else None,
                            "attendance_date": b.attendance_date.isoformat() if b.attendance_date else None,
                            "total_amount": b_total,
                            "total_amount_paid": b_paid,
                            "amount_paid": safe_float(b.amount_paid),
                            "outstanding": round(b_total - b_paid, 2),
                            "payment_type": b.payment_type,
                            "payment_method": b.payment_method
                        })
                    else:
                        bills_info.append({"billing_no": bno, "found": False})
        except Exception as e:
            print(f"Error fetching bills for {a.registration_number}: {e}")
            bills_info = [{"error": str(e)}]

        attendance_obj["billing_info"] = bills_info

        result.append({
            "registration_number": a.registration_number,
            "child_details": reg_map.get(a.registration_number),
            "attendance": attendance_obj
        })

    # 6) Return response with real data
    return Response({
        "status": "success",
        "count": len(result),
        "data": result
    })

# --- 1. MongoDB Connection Setup ---
env_type = os.environ.get("ENV_CLASSIFICATION", "local")
mongo_uri = os.environ.get("GLOBAL_DB_HOST")
db_name = os.environ.get("MILESTONE_DB_NAME", "Milestone")

if env_type in ["test", "prod"]:
    client = MongoClient(mongo_uri)
else:
    client = MongoClient(mongo_uri)

db = client[db_name]
old_therapy_billing_col = db["milestone_backend_oldtherapybilling"]

@api_view(['GET'])
@permission_classes([HasRolePermission]) # Uncomment when ready
def get_oldtherapy_reports(request):
    try:
        from_date_str = request.GET.get('from_date')
        to_date_str = request.GET.get('to_date')

        # --- 2. Date Filtering Logic ---
        from_date = None
        to_date = None

        if from_date_str:
            try:
                from_date = datetime.strptime(from_date_str, '%Y-%m-%d').replace(
                    hour=0, minute=0, second=0, tzinfo=timezone.utc
                )
            except ValueError:
                return Response({"error": "Invalid from_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        
        if to_date_str:
            try:
                parsed_to_date = datetime.strptime(to_date_str, '%Y-%m-%d').replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
                to_date = parsed_to_date + timedelta(seconds=1)
            except ValueError:
                return Response({"error": "Invalid to_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        # --- 3. Construct Query ---
        mongo_filter = {}
        if from_date or to_date:
            mongo_filter['date'] = {}
            if from_date:
                mongo_filter['date']['$gte'] = from_date
            if to_date:
                mongo_filter['date']['$lt'] = to_date

        # --- 4. Fetch and Transform Data ---
        # Sort by date descending so newest reports appear first
        cursor = old_therapy_billing_col.find(mongo_filter).sort('date', -1)

        results = []
        for doc in cursor:
            # A. Handle ObjectId
            if '_id' in doc:
                doc['id'] = str(doc.pop('_id'))

            # B. Parse Stringified JSON Fields
            # The frontend has checks for strings, but it's cleaner to send objects if possible.
            # We attempt to parse these fields.
            fields_to_parse = [
                'nameoftherapy', 
                'consultant_doctor', 
                'remaining_amount', 
                'age'
            ]
            
            for field in fields_to_parse:
                if field in doc and isinstance(doc[field], str):
                    try:
                        doc[field] = json.loads(doc[field])
                    except (json.JSONDecodeError, TypeError):
                        # If parsing fails, we keep the original string/value 
                        # so the frontend doesn't crash (it has fallback logic)
                        pass

            # C. Map specific fields for Frontend Table
            
            # 1. Map 'father_phone_number' to 'phone' 
            # The frontend table body uses {item.phone}, but export uses father/mother.
            # We default 'phone' to father_phone_number.
            doc['phone'] = doc.get('father_phone_number') or doc.get('mother_phone_number', '')

            # 2. Map 'session' to 'number_of_sessions'
            # Your previous JSON showed a field "session", but frontend asks for "number_of_sessions".
            if 'session' in doc:
                doc['number_of_sessions'] = doc['session']
            elif 'number_of_sessions' not in doc:
                doc['number_of_sessions'] = 0 # Default if missing

            # 3. Ensure 'discount_remarks' exists
            if 'discount_remarks' not in doc:
                doc['discount_remarks'] = "-"

            results.append(doc)

        return Response(results, status=status.HTTP_200_OK)

    except Exception as e:
        # It is good practice to log the actual error for debugging
        print(f"Error in therapy_reports: {str(e)}")
        return Response(
            {"error": "An internal server error occurred processing the report."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )