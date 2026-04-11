from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime
from milestone_backend.models import DevelopmentGoals
from milestone_backend.serializers import DevelopmentGoalsSerializer
from pyauth.auth import HasRolePermission
import calendar

@api_view(["POST", "GET"])
# @permission_classes([HasRolePermission])
def development_goals_list_create(request):
    employee_id = request.data.get('auth-user-id')

    if request.method == "POST":
        data = request.data.copy()
        reg_number = data.get('registration_number')
        date_str = data.get('date')

        if not reg_number or not date_str:
            return Response({"error": "registration_number and date are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if a record exists for this patient in the same month and year
        # Djongo doesn't support date__year and date__month lookup reliably
        first_day = date_obj.replace(day=1)
        last_day = date_obj.replace(day=calendar.monthrange(date_obj.year, date_obj.month)[1])

        # Ensure registration_number is a clean string
        clean_reg = str(reg_number).strip().lower()
        
        # Robust per-patient check
        month_records = DevelopmentGoals.objects.filter(date__range=(first_day, last_day))
        existing_record = None
        for rec in month_records:
            if str(rec.registration_number).strip().lower() == clean_reg:
                existing_record = rec
                break

        if existing_record:
            # Smart Update (Upsert logic)
            serializer = DevelopmentGoalsSerializer(existing_record, data=data, partial=True)
            if serializer.is_valid():
                serializer.save(
                    lastmodified_by=employee_id,
                    lastmodified_date=timezone.now()
                )
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Create New Record
        serializer = DevelopmentGoalsSerializer(data=data)
        if serializer.is_valid():
            serializer.save(
                created_by=employee_id,
                created_date=timezone.now(),
                lastmodified_by=employee_id,
                lastmodified_date=timezone.now()
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # GET logic
    reg_number = request.query_params.get('registration_number')
    if reg_number:
        qs = DevelopmentGoals.objects.filter(registration_number=reg_number).order_by('-date')
    else:
        qs = DevelopmentGoals.objects.all().order_by('-date')
        
    serializer = DevelopmentGoalsSerializer(qs, many=True)
    return Response(serializer.data)

@api_view(["GET", "PUT", "PATCH", "DELETE"])
# @permission_classes([HasRolePermission])
def development_goals_detail(request, pk):
    try:
        instance = DevelopmentGoals.objects.get(pk=pk)
    except DevelopmentGoals.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    employee_id = request.data.get('auth-user-id')

    if request.method == "GET":
        serializer = DevelopmentGoalsSerializer(instance)
        return Response(serializer.data)

    elif request.method in ["PUT", "PATCH"]:
        serializer = DevelopmentGoalsSerializer(instance, data=request.data, partial=(request.method == "PATCH"))
        if serializer.is_valid():
            serializer.save(
                lastmodified_by=employee_id,
                lastmodified_date=timezone.now()
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
