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
from pyauth.auth import HasRolePermission
from pymongo import MongoClient
from django.http import JsonResponse
from django.utils.timezone import now
from ..models import TherapyBilling, PatientAssessment,OthersBilling
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
    client = MongoClient(mongo_uri)

@api_view(['GET'])
@permission_classes([HasRolePermission])
def pendingPayment(request):
    try:
        # Step 1: Get all records first to debug
        all_records = TherapyBilling.objects.all()
        print(f"Total records in database: {all_records.count()}")
        
        # Step 2: Get the latest billing entry for each unique combination
        latest_bills = (
            TherapyBilling.objects.values(
                "name", "dob", "nameoftherapy", "father_phone_number", 
                "mother_phone_number", "age", "sex"
            )
            .annotate(latest_billing_no=Max("billing_no"))
        )
        
        print(f"Latest bills count: {len(latest_bills)}")
        for bill in latest_bills:
            print(f"Latest bill: {bill}")
        
        # Step 3: Fetch the latest records based on billing_no
        latest_records = TherapyBilling.objects.filter(
            billing_no__in=[entry["latest_billing_no"] for entry in latest_bills]
        )
        
        print(f"Latest records count: {latest_records.count()}")
        
        # Step 4: Debug each record's remaining_amount field
        pending_records = []
        for record in latest_records:
            print(f"\n--- Processing record: {record.billing_no} ---")
            print(f"Name: {record.name}")
            print(f"Remaining amount raw: {record.remaining_amount}")
            print(f"Remaining amount type: {type(record.remaining_amount)}")
            
            try:
                # Handle different possible data types
                if isinstance(record.remaining_amount, str):
                    remaining_amount_data = json.loads(record.remaining_amount)
                elif isinstance(record.remaining_amount, dict):
                    remaining_amount_data = record.remaining_amount
                else:
                    print(f"Unexpected type for remaining_amount: {type(record.remaining_amount)}")
                    continue
                
                print(f"Parsed remaining_amount: {remaining_amount_data}")
                
                status = remaining_amount_data.get('status')
                value = remaining_amount_data.get('value', 0)
                
                print(f"Status: {status}, Value: {value}")
                
                # Check if status is "Pending" and value is greater than 0
                if status == 'Pending' and value > 0:
                    print(f"✓ Record {record.billing_no} added to pending_records")
                    pending_records.append(record)
                else:
                    print(f"✗ Record {record.billing_no} NOT added - Status: {status}, Value: {value}")
                    
            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                print(f"Error parsing remaining_amount for {record.billing_no}: {e}")
                continue
        
        print(f"\nFinal pending records count: {len(pending_records)}")
        
        # Step 5: Serialize and return
        serializer = TherapyBillingSerializer(pending_records, many=True)
        return Response(serializer.data, status=200)
        
    except Exception as e:
        print(f"Error in pendingPayment view: {e}")
        return Response({"error": str(e)}, status=500)



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
    latest_others_billing = OthersBilling.objects.filter(billing_no__startswith=prefix).order_by('-billing_no').first()


    latest_billing_no = 0  # Default start value

    # Extract numeric part and determine the highest billing number
    if latest_therapy_billing and latest_therapy_billing.billing_no:
        latest_billing_no = max(latest_billing_no, extract_numeric_part(latest_therapy_billing.billing_no))
    
    if latest_assessment_billing and latest_assessment_billing.billing_no:
        latest_billing_no = max(latest_billing_no, extract_numeric_part(latest_assessment_billing.billing_no))
        
    if latest_others_billing and latest_others_billing.billing_no:
        latest_billing_no = max(latest_billing_no, extract_numeric_part(latest_others_billing.billing_no))

    # Generate the new billing number with six-digit counter
    new_billing_no = f"{prefix}{str(latest_billing_no + 1).zfill(6)}"
    
    return JsonResponse({'billing_no': new_billing_no})



@api_view(['PATCH'])
@permission_classes([HasRolePermission])
def update_payment(request):
    db = client[db_name]          
    therapy_collection = db['milestone_backend_therapybilling']
    assessment_collection = db['milestone_backend_patientassessment']

    data = request.data
    age = data.get('age')
    billing_no = data.get('billing_no')
    paid_amount = data.get('paid_amount', 0)  # Remove float() conversion
    discount = data.get('discount', 0)  # Remove float() conversion
    discount_remarks = data.get('discount_remarks', "")
    payment_method = data.get('payment_method', "")
    
    # Extract employee ID for audit tracking
    employee_id = data.get('auth-user-id')

    if not billing_no or paid_amount < 0 or discount < 0:
        return JsonResponse({'error': 'Invalid billing number, amount, or discount.'}, status=400)

    # Fetch the existing bill
    patient = therapy_collection.find_one({'billing_no': billing_no})
    if not patient:
        return JsonResponse({'error': 'Patient not found.'}, status=404)

    # Parse remaining amount (handle both object and numeric formats)
    remaining_amount_data = patient.get('remaining_amount', 0)
    if isinstance(remaining_amount_data, str):
        try:
            remaining_amount_obj = json.loads(remaining_amount_data)
            remaining_amount = remaining_amount_obj.get('value', 0)  # Remove float() conversion
        except (json.JSONDecodeError, ValueError):
            remaining_amount = remaining_amount_data  # Remove float() conversion
    elif isinstance(remaining_amount_data, dict):
        remaining_amount = remaining_amount_data.get('value', 0)  # Remove float() conversion
    else:
        remaining_amount = remaining_amount_data  # Remove float() conversion

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

    # Calculate new remaining amount
    new_remaining_amount_value = remaining_amount - paid_amount - discount
    
    # Get current Indian time
    from pytz import timezone as pytz_timezone
    indian_tz = pytz_timezone('Asia/Kolkata')
    current_indian_time = datetime.now(indian_tz)
    
    # Determine status based on remaining amount
    if new_remaining_amount_value <= 0:
        status = "Paid"
        paid_date = current_indian_time.strftime("%d/%m/%Y, %H:%M:%S")
        new_remaining_amount_value = 0
    else:
        status = "Pending"
        paid_date = None

    # Create remaining_amount as JSON object for new bill (new_bill_no should be null)
    remaining_amount_json = json.dumps({
        "value": new_remaining_amount_value,
        "status": status,
        "paid_date": paid_date,
        "new_bill_no": None
    })

    # Copy patient data to create a new bill
    new_bill = patient.copy()
    new_bill.pop("_id", None)  # Remove MongoDB _id to avoid duplication
    new_bill["billing_no"] = new_billing_no
    new_bill["amount_paid"] = paid_amount
    new_bill["therapy_charge"] = remaining_amount  # Update therapy_charge with previous remaining_amount
    new_bill["adjusted_charge"] = new_bill["therapy_charge"] - discount  # Adjusted charge after discount
    new_bill["remaining_amount"] = remaining_amount_json  # Store as JSON string
    new_bill["discount"] = discount
    new_bill["discount_remarks"] = discount_remarks
    new_bill["payment_method"] = payment_method
    new_bill["age"] = age
    new_bill["date"] = current_indian_time  # Store current Indian time
    
    # Add audit fields for the new bill
    if employee_id:
        new_bill["created_by"] = employee_id
        new_bill["created_date"] = current_indian_time

    # Insert new bill into the database
    therapy_collection.insert_one(new_bill)
    
    # Update the previous bill - only update with JSON containing new_bill_no
    # Keep the original remaining_amount value, just update other fields
    previous_remaining_amount_obj = {
        "value": remaining_amount,  # Keep original remaining amount
        "status": "Paid",
        "paid_date": current_indian_time.strftime("%d/%m/%Y, %H:%M:%S"),
        "new_bill_no": new_billing_no
    }
    previous_remaining_amount_json = json.dumps(previous_remaining_amount_obj)
    
    # Prepare update fields for the previous bill (only JSON and audit fields)
    update_fields = {
        'remaining_amount': previous_remaining_amount_json
    }
    
    # Add audit fields for the update
    if employee_id:
        update_fields['lastmodified_by'] = employee_id
        update_fields['lastmodified_date'] = current_indian_time
    
    therapy_collection.update_one(
        {'billing_no': billing_no},
        {'$set': update_fields}
    )

    return JsonResponse({
        'message': 'Payment updated successfully.',
        'new_bill_no': new_billing_no,
        'remaining_amount': new_remaining_amount_value,
        'status': status
    }, status=200)
