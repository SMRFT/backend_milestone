from rest_framework.decorators import api_view
from rest_framework.response import Response
from ..models import TherapyBilling
from ..serializers import TherapyBillingSerializer
from django.db.models import Max
from django.http import JsonResponse
from rest_framework.decorators import api_view , permission_classes
from pymongo import MongoClient
from urllib.parse import quote_plus
import json
import re
from datetime import datetime, timezone
from ..auth.permissions import SkipPermissionsIfDisabled
from pyauth.auth import HasRoleAndDataPermission
from pymongo import MongoClient
import gridfs

import os
import certifi
from dotenv import load_dotenv

load_dotenv()  # Load from .env if present

env_type = os.environ.get("ENV_CLASSIFICATION", "local")

mongo_uri = os.environ.get("GLOBAL_DB_HOST")
db_name = os.environ.get("MILESTONE_DB_NAME", "Milestone")

if env_type in ["test", "prod"]:
    client = MongoClient(mongo_uri)
else:
    client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())

@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def pendingPayment(request):
    # Get the latest billing entry for each unique combination of specified fields
    latest_bills = (
        TherapyBilling.objects.values(
            "name", "nameoftherapy", "father_phone_number","mother_phone_number", "age", "sex"
        )
        .annotate(latest_billing_no=Max("billing_no"))
    )

    # Fetch the latest records based on billing_no
    latest_records = TherapyBilling.objects.filter(
        billing_no__in=[entry["latest_billing_no"] for entry in latest_bills]
    )

    serializer = TherapyBillingSerializer(latest_records, many=True)
    return Response(serializer.data, status=200)


from django.http import JsonResponse
from django.utils.timezone import now
from ..models import TherapyBilling, PatientAssessment
import re

def get_financial_year():
    """Returns the last two digits of the financial year (April - March cycle)."""
    current_date = now()
    year = current_date.year % 100  # Get last two digits of the year
    if current_date.month < 4:  # Before April, use previous year
        year -= 1
    return str(year)

def extract_numeric_part(billing_no):
    """Extracts the numeric part from billing number (e.g., 'MDC25/000001' → 1)."""
    match = re.search(r'(\d+)$', billing_no)
    return int(match.group(1)) if match else 0

def get_latest_billing_no(request):
    current_financial_year = get_financial_year()
    prefix = f"MDC{current_financial_year}/"  # Fix: Move MDC before year

    # Fetch the latest billing numbers from both models for the current financial year
    latest_therapy_billing = TherapyBilling.objects.filter(billing_no__startswith=prefix).order_by('-billing_no').first()
    latest_assessment_billing = PatientAssessment.objects.filter(billing_no__startswith=prefix).order_by('-billing_no').first()

    latest_billing_no = 0  # Default start value

    # Extract numeric part and determine the highest billing number
    if latest_therapy_billing and latest_therapy_billing.billing_no:
        latest_billing_no = max(latest_billing_no, extract_numeric_part(latest_therapy_billing.billing_no))
    
    if latest_assessment_billing and latest_assessment_billing.billing_no:
        latest_billing_no = max(latest_billing_no, extract_numeric_part(latest_assessment_billing.billing_no))

    # Generate the new billing number with six-digit counter
    new_billing_no = f"{prefix}{str(latest_billing_no + 1).zfill(6)}"
    
    return JsonResponse({'billing_no': new_billing_no})




def get_financial_year():
    """Returns the last two digits of the financial year (April - March cycle)."""
    current_date = datetime.now(timezone.utc)
    year = current_date.year % 100  # Get last two digits of the year
    if current_date.month < 4:  # Before April, use previous year
        year -= 1
    return str(year)

def extract_numeric_part(billing_no):
    """Extracts the numeric part from billing number (e.g., '25MDC/000001' → 1)."""
    match = re.search(r'(\d+)$', billing_no)
    return int(match.group(1)) if match else 0

@api_view(['PATCH'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def update_payment(request):
    db = client[db_name]          
    therapy_collection = db['milestone_backend_therapybilling']
    assessment_collection = db['milestone_backend_patientassessment']

    data = json.loads(request.body)
    billing_no = data.get('billing_no')
    paid_amount = float(data.get('paid_amount', 0))
    discount = float(data.get('discount', 0))
    discount_remarks = data.get('discount_remarks', "")

    if not billing_no or paid_amount < 0 or discount < 0:
        return JsonResponse({'error': 'Invalid billing number, amount, or discount.'}, status=400)

    # Fetch the existing bill
    patient = therapy_collection.find_one({'billing_no': billing_no})
    if not patient:
        return JsonResponse({'error': 'Patient not found.'}, status=404)

    remaining_amount = float(patient.get('remaining_amount', 0))
    adjusted_charge = float(patient.get('adjusted_charge', 0))
    amount_paid = float(patient.get('amount_paid', 0))

    if paid_amount + discount > remaining_amount:
        return JsonResponse({'error': 'Total payment + discount exceeds remaining balance.'}, status=400)

    # Determine financial year and prefix
    current_financial_year = get_financial_year()
    prefix = f"MDC{current_financial_year}/"

    # Fetch latest billing_no for the current financial year
    latest_therapy = therapy_collection.find_one(
        {"billing_no": {"$regex": f"^{prefix}"}},
        sort=[("billing_no", -1)]
    )
    latest_assessment = assessment_collection.find_one(
        {"billing_no": {"$regex": f"^{prefix}"}},
        sort=[("billing_no", -1)]
    )

    latest_billing_no = 0

    # Extract numeric part from latest billing numbers
    if latest_therapy and latest_therapy.get("billing_no"):
        latest_billing_no = max(latest_billing_no, extract_numeric_part(latest_therapy["billing_no"]))

    if latest_assessment and latest_assessment.get("billing_no"):
        latest_billing_no = max(latest_billing_no, extract_numeric_part(latest_assessment["billing_no"]))

    # Generate the new billing number with six digits
    new_billing_no = f"{prefix}{str(latest_billing_no + 1).zfill(6)}"

    # Copy patient data to create a new bill
    new_bill = patient.copy()
    new_bill.pop("_id", None)  # Remove MongoDB _id to avoid duplication
    new_bill["billing_no"] = new_billing_no
    new_bill["amount_paid"] = paid_amount
    new_bill["therapy_charge"] = remaining_amount  # Update therapy_charge with previous remaining_amount
    new_bill["total_amount"] = new_bill["therapy_charge"]  # Update total_amount with previous remaining_amount
    new_bill["others"] = ""    
    new_bill["othersprice"] = 0  
    new_bill["adjusted_charge"] = new_bill["therapy_charge"] - discount  # Adjusted charge after discount

    # Calculate new remaining_amount
    new_bill["remaining_amount"] = new_bill["therapy_charge"] - paid_amount - discount

    new_bill["discount"] = discount
    new_bill["discount_remarks"] = discount_remarks
    new_bill["date"] = datetime.now(timezone.utc)  # Store current UTC date

    # Insert new bill into the database
    therapy_collection.insert_one(new_bill)

    return JsonResponse({
        'message': 'Payment updated successfully.',
        'new_bill_no': new_billing_no
    }, status=200)
