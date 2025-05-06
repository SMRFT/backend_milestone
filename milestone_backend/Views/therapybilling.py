from datetime import datetime
import json
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.decorators import api_view , permission_classes
from rest_framework.response import Response
from datetime import datetime, timezone, timedelta


from ..models import TherapyBilling
from ..serializers import TherapyBillingSerializer


from ..auth.permissions import SkipPermissionsIfDisabled
from pyauth.auth import HasRoleAndDataPermission


@csrf_exempt
@api_view(['POST'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def therapy_billing(request):
    from .invoice import get_latest_billing_no  # Move import inside function

    serializer = TherapyBillingSerializer(data=request.data)
    if serializer.is_valid():
        therapy_billing_instance = TherapyBilling(**serializer.validated_data)

        # Automatically set the date and time
        therapy_billing_instance.date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not therapy_billing_instance.billing_no:
            latest_billing_response = get_latest_billing_no(None)
            latest_billing_data = json.loads(latest_billing_response.content.decode())
            therapy_billing_instance.billing_no = latest_billing_data.get('billing_no', '001')

        therapy_billing_instance.save()
        return Response(TherapyBillingSerializer(therapy_billing_instance).data, status=201)

    return Response(serializer.errors, status=400)




@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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

