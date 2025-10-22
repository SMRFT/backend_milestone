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

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from pymongo import MongoClient, DESCENDING
from datetime import datetime
import os, json

from rest_framework.decorators import api_view
from rest_framework.response import Response
from pymongo import MongoClient, DESCENDING
import os, json

@api_view(['GET'])
def pending_payment_report(request):
    mongo_uri = os.environ.get("GLOBAL_DB_HOST")
    client = MongoClient(mongo_uri)
    db = client["Milestone"]

    attendance_col = db['milestone_backend_patientattendance']
    billing_col = db['milestone_backend_therapybilling']
    registration_col = db['milestone_backend_registration']

    result = []

    # Fetch all billings once to optimize
    all_billings = list(billing_col.find())

    # ✅ Only active attendance
    for attendance in attendance_col.find({"is_active": True}):
        reg_no = attendance.get('registration_number')
        therapy_charge = float(attendance.get('therapy_charge', 0))
        att_date = attendance.get('date')

        # Get registration details
        registration = registration_col.find_one({'registration_number': reg_no})
        if not registration:
            continue

        name = registration.get('name_of_child')
        gender = registration.get('sex')
        dob = registration.get('dob')
        age = registration.get('age')

        # Parse age if stored as string
        if isinstance(age, str):
            try:
                age = json.loads(age)
            except:
                age = {}

        # --- Check for duplicate: same date in billing ---
        duplicate_found = False
        for bill in all_billings:
            if bill.get('registration_number') == reg_no:
                bill_date = bill.get('date')
                if bill_date and att_date:
                    # Compare date (ignore time)
                    if bill_date.date() == att_date.date():
                        duplicate_found = True
                        break

        if duplicate_found:
            continue  # Skip duplicate entries (already billed same date)

        # --- Get latest billing (if not same date) ---
        last_billing = billing_col.find({'registration_number': reg_no}).sort('date', DESCENDING).limit(1)
        last_billing = list(last_billing)

        if not last_billing:
            # No billing found → full therapy charge pending
            result.append({
                "date": att_date,
                "registration_number": reg_no,
                "name": name,
                "dob": dob,
                "age": age,
                "gender": gender,
                "therapy_charge": therapy_charge,
                "amount_pending": therapy_charge
            })
            continue

        last_bill = last_billing[0]
        remaining_json = last_bill.get('remaining_amount', {})
        remaining_value = 0.0

        if isinstance(remaining_json, str):
            try:
                remaining_json = json.loads(remaining_json.replace("'", '"'))
            except:
                remaining_json = {}

        remaining_value = float(remaining_json.get('value', 0))

        # If remaining amount not available, set it as therapy charge
        amount_pending = remaining_value if remaining_value > 0 else therapy_charge

        result.append({
            "date": att_date,
            "registration_number": reg_no,
            "name": name,
            "dob": dob,
            "age": age,
            "gender": gender,
            "therapy_charge": therapy_charge,
            "amount_pending": amount_pending
        })

    return Response(result, status=status.HTTP_200_OK)
