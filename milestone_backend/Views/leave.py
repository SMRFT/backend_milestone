from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from ..models import leaveform, Registration
from ..serializers import LeaveFormSerializer, RegistrationSerializer
from pyauth.auth import HasRolePermission
import json

@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_pending_leaves(request):
    """
    Fetch all pending leave requests.
    Joins with Registration to get patient details.
    """
    try:
        pending_leaves = leaveform.objects.filter(leave_status="Pending")
        serializer = LeaveFormSerializer(pending_leaves, many=True)
        
        # Join with registration data
        response_data = []
        for leave in serializer.data:
            registration = Registration.objects.filter(registration_number=leave['registration_number']).first()
            patient_info = RegistrationSerializer(registration).data if registration else {}
            response_data.append({
                **patient_info,
                "leave_details": leave
            })
            
        return Response({
            "status": "success",
            "count": len(response_data),
            "data": response_data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([HasRolePermission])
def submit_leave(request):
    """
    Submit a new leave request.
    """
    try:
        data = request.data.copy()
        data['leave_status'] = "Pending"
        serializer = LeaveFormSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PATCH'])
@permission_classes([HasRolePermission])
def update_leave_status(request):
    """
    Approve or Reject a leave request.
    If rejected, leave_reject_comments is mandatory.
    Using .update() to avoid duplicates in Djongo/MongoDB.
    """
    try:
        registration_number = request.data.get("registration_number")
        leave_date = request.data.get("leave_date")
        new_status = request.data.get("leave_status") # 'Approved' or 'Rejected'
        reject_comments = request.data.get("leave_reject_comments", "")
        approved_by = request.data.get("auth-user-id", "Admin")

        if not registration_number or not leave_date or not new_status:
            return Response({"status": "error", "message": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

        # Use QuerySet update to prevent duplicate generation issues in some Djongo scenarios
        leave_request_qs = leaveform.objects.filter(registration_number=registration_number, leave_date=leave_date)
        
        if not leave_request_qs.exists():
            return Response({"status": "error", "message": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)

        if new_status == "Rejected" and not reject_comments:
            return Response({"status": "error", "message": "Remark is mandatory for rejection."}, status=status.HTTP_400_BAD_REQUEST)

        update_values = {
            'leave_status': new_status,
            'leave_approved_by': approved_by,
            'leave_approved_date': timezone.now().date(),
        }
        
        if new_status == "Rejected":
            update_values['leave_reject_comments'] = reject_comments
        else:
            update_values['leave_reject_comments'] = None # Clear if approved later?
            
        leave_request_qs.update(**update_values)
        
        return Response({
            "status": "success",
            "message": f"Leave request {new_status.lower()} successfully."
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_leaves_report(request):
    """
    Fetch leave reports (Approved/Rejected/Pending) with date filter.
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        status_filter = request.GET.get('leave_status') # Optional
        
        query = {}
        if start_date and end_date:
            query['leave_date__range'] = [start_date, end_date]
        elif start_date:
            query['leave_date__gte'] = start_date
        elif end_date:
            query['leave_date__lte'] = end_date
            
        if status_filter:
            query['leave_status'] = status_filter
            
        leaves = leaveform.objects.filter(**query).order_by('-leave_date')
        serializer = LeaveFormSerializer(leaves, many=True)
        
        response_data = []
        for leave in serializer.data:
            registration = Registration.objects.filter(registration_number=leave['registration_number']).first()
            patient_info = RegistrationSerializer(registration).data if registration else {}
            response_data.append({
                **patient_info,
                "leave_details": leave
            })
            
        return Response({
            "status": "success",
            "count": len(response_data),
            "data": response_data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
