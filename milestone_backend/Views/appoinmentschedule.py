import os
from datetime import datetime, date as date_cls
from django.db.models import Q
from django.utils import timezone
 
from pymongo import MongoClient
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
 
from ..models import AppointmentSchedule, EnquiryForm, Registration
from ..serializers import AppointmentScheduleSerializer, EnquiryFormSerializer
from .dbcollection import profile_collection
from datetime import datetime, date as date_cls


import os
from .dbcollection import dailytimeslot_collection

from pyauth.auth import HasRolePermission
from rest_framework.decorators import api_view, permission_classes


@api_view(["GET"])
@permission_classes([HasRolePermission])
def get_dailytimeslot(request):
    try:
        slots = list(
            dailytimeslot_collection.find(
                {"is_active": True},
                {"_id": 0}
            ).sort("sequence", 1)
        )

        return Response({
            "success": True,
            "data": slots
        })

    except Exception as e:
        return Response({
            "success": False,
            "error": str(e)
        })


@api_view(["GET"])
@permission_classes([HasRolePermission])
def get_all_therapists(request):
    """
    Returns therapists/doctors who can be booked.
    """
    try:
        query = {
            "$or": [
                {"primaryRole": {"$in": ["MDC-R-ADM", "MDC-R-PDC"]}},
                {"additionalRoles": {"$in": ["MDC-R-ADM", "MDC-R-PDC"]}},
            ]
        }

        projection = {
            "_id": 0,
            "employeeId": 1,
            "employeeName": 1
        }

        data = list(profile_collection.find(query, projection))

        return Response({
            "success": True,
            "data": data
        })

    except Exception as e:
        return Response({
            "success": False,
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


 
@api_view(["GET"])
@permission_classes([HasRolePermission])
def get_appointments_by_date(request):
    """
    Returns all booked appointments for a given date, grouped so the
    frontend can mark slots as taken per therapist.
    Query param: ?date=YYYY-MM-DD (defaults to today)
    """
    date_str = request.GET.get("date")
    try:
        target_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date_cls.today()
        )
    except ValueError:
        return Response({"success": False, "error": "Invalid date format, expected YYYY-MM-DD"}, status=400)
 
    appointments = AppointmentSchedule.objects.filter(date=target_date).exclude(status="Cancelled")
    serializer = AppointmentScheduleSerializer(appointments, many=True)
    return Response({"success": True, "data": serializer.data})
 
 
# NOTE: add this import at the top of your views.py if it isn't already there —
# it's needed for the OR-style clash query below.
from django.db.models import Q
 
 
@api_view(["POST"])
@permission_classes([HasRolePermission])
def create_appointment(request):
    """
    Books an appointment. Expects:
    {
        "date": "2026-07-01",
        "name_of_child": "...",
        "registration_number": "MDC/xxx/2026",
        "therapist_id": "...",
        "slot_label": "10.15-11.00",
        "slot_start_time": "10:15",
        "slot_end_time": "11:00",
        "status": "Scheduled",
        "notes": ""
    }
    """
 
    payload = request.data.copy()
 
    # ✅ Date validation
    try:
        appt_date = datetime.strptime(payload.get("date"), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return Response(
            {"success": False, "error": "A valid 'date' (YYYY-MM-DD) is required."},
            status=400
        )
 
    if appt_date < date_cls.today():
        return Response(
            {"success": False, "error": "Cannot book an appointment on a past date."},
            status=400
        )
 
    # ✅ Slot validation
    slot_start = payload.get("slot_start_time")
    if not slot_start:
        return Response(
            {"success": False, "error": "'slot_start_time' is required."},
            status=400
        )
 
    slot_end = payload.get("slot_end_time")
    if not slot_end:
        return Response(
            {"success": False, "error": "'slot_end_time' is required."},
            status=400
        )
 
    # ✅ Status (no validation, frontend handles it)
    status_value = payload.get("status")
    if not status_value:
        return Response(
            {"success": False, "error": "Status is required."},
            status=400
        )
 
    # ✅ Combine date + time
    payload["appointment_datetime"] = f"{payload.get('date')}T{slot_start}:00"
 
    # ✅ Created by from header
    employee_id = request.data.get('auth-user-id')
 
    # ✅ Save
    serializer = AppointmentScheduleSerializer(data=payload)
    if serializer.is_valid():
        serializer.save(created_by=employee_id)
        child_name = serializer.data.get("name_of_child", "")
        return Response(
            {
                "success": True,
                "data": serializer.data,
                "message": f"Appointment booked for {child_name}." if child_name else "Appointment booked.",
            },
            status=status.HTTP_201_CREATED
        )
 
    return Response(
        {"success": False, "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST
    )
 


@api_view(["PATCH"])
@permission_classes([HasRolePermission])
def update_appointment_status(request):
    """
    Reschedule:
    { "appointment_id": 2, "status": "Rescheduled", "rescheduled_therapist_id": "<new therapist id>" }
 
    Cancel:
    { "appointment_id": 2, "status": "Cancelled", "cancel_reason": "Patient requested a different day" }
    """
    appointment_id = request.data.get("appointment_id")
    new_status = request.data.get("status")
 
    if not appointment_id:
        return Response({"success": False, "error": "'appointment_id' is required."}, status=400)
    if not new_status:
        return Response({"success": False, "error": "'status' is required."}, status=400)
 
    try:
        appointment = AppointmentSchedule.objects.get(appointment_id=appointment_id)
    except AppointmentSchedule.DoesNotExist:
        return Response({"success": False, "error": "Appointment not found."}, status=404)
 
    # ✅ Cancel is allowed from either Scheduled or Rescheduled (so a
    # rescheduled appointment can still be cancelled). A further reschedule
    # is only allowed while still Scheduled — checked separately below.
    if new_status == "Cancelled":
        if appointment.status not in ("Scheduled", "Rescheduled"):
            return Response(
                {"success": False, "error": "Only scheduled or rescheduled appointments can be cancelled."},
                status=400
            )
    else:
        if appointment.status != "Scheduled":
            return Response({"success": False, "error": "Only scheduled appointments can be updated."}, status=400)
 
    message = None
    employee_id = request.data.get("auth-user-id")
 
    if new_status == "Rescheduled":
        # Frontend sends the reassigned doctor as rescheduled_therapist_id.
        new_therapist_id = request.data.get("rescheduled_therapist_id")
        if not new_therapist_id:
            return Response(
                {"success": False, "error": "'rescheduled_therapist_id' is required to reschedule."},
                status=400
            )
 
        # ✅ therapist_id is the doctor the appointment was originally booked
        # with and is never touched. The doctor currently holding the slot is
        # therapist_id for a plain "Scheduled" appointment, or
        # rescheduled_therapist_id for one that's already been "Rescheduled" —
        # so the clash check has to look at both to correctly detect a
        # double-booking for the incoming doctor.
        clash = AppointmentSchedule.objects.filter(
            date=appointment.date,
            slot_start_time=appointment.slot_start_time,
            slot_end_time=appointment.slot_end_time,
        ).exclude(appointment_id=appointment.appointment_id).filter(
            Q(status="Scheduled", therapist_id=new_therapist_id) |
            Q(status="Rescheduled", rescheduled_therapist_id=new_therapist_id)
        ).exists()
        if clash:
            return Response({"success": False, "error": "That doctor already has a booking in this slot."}, status=400)
 
        # ✅ Only rescheduled_therapist_id is updated. therapist_id (the
        # original booking) is deliberately left unchanged.
        appointment.rescheduled_therapist_id = new_therapist_id
        appointment.status = "Rescheduled"
        message = f"Appointment for {appointment.name_of_child} has been rescheduled."
 
    elif new_status == "Cancelled":
        cancel_reason = request.data.get("cancel_reason")
        if not cancel_reason:
            return Response({"success": False, "error": "'cancel_reason' is required to cancel."}, status=400)
        appointment.status = "Cancelled"
        appointment.isactive = False
        appointment.cancel_reason = cancel_reason
        # ✅ who cancelled it and when, from the same auth-user-id field
        # create_appointment uses for created_by.
        appointment.cancelled_by = employee_id
        appointment.cancelled_datetime = timezone.now()
        message = f"Appointment for {appointment.name_of_child} has been cancelled."
 
    else:
        appointment.status = new_status
        message = f"Appointment for {appointment.name_of_child} updated to {new_status}."
 
    # lastmodified_by/lastmodified_date are stamped on every update.
    appointment.lastmodified_by = employee_id
    appointment.lastmodified_date = timezone.now()
    appointment.save()
 
    serializer = AppointmentScheduleSerializer(appointment)
    return Response({"success": True, "data": serializer.data, "message": message})




# appoinmentschedule.py — add this to the existing file (alongside
# create_appointment / update_appointment_status). Reuses the same imports
# those already rely on (api_view, permission_classes, Response, status,
# HasRolePermission, AppointmentSchedule, AppointmentScheduleSerializer) —
# only the two new ones below need adding.





ADMIN_ROLE = "MDC-R-ADM"
RECEPTIONIST_ROLE = "MDC-R-REC"


def _roles_for(profile):
    """Flatten primaryRole + additionalRoles from a Global-db profile doc."""
    if not profile:
        return []
    roles = []
    primary = profile.get("primaryRole")
    if primary:
        roles.append(primary)
    roles.extend(profile.get("additionalRoles") or [])
    return roles


def _format_slot_time(appt):
    start = appt.slot_start_time.strftime("%H:%M") if appt.slot_start_time else None
    end = appt.slot_end_time.strftime("%H:%M") if appt.slot_end_time else None
    if start and end:
        return f"{start}-{end}"
    return start or end or ""


ADMIN_ROLE = "MDC-R-ADM"
RECEPTIONIST_ROLE = "MDC-R-REC"
THERAPIST_ROLE = "MDC-R-PDC"
 
 
def _roles_for(profile):
    """Flatten primaryRole + additionalRoles from a Global-db profile doc."""
    if not profile:
        return []
    roles = []
    primary = profile.get("primaryRole")
    if primary:
        roles.append(primary)
    roles.extend(profile.get("additionalRoles") or [])
    return roles
 
 
def _format_slot_time(appt):
    start = appt.slot_start_time.strftime("%H:%M") if appt.slot_start_time else None
    end = appt.slot_end_time.strftime("%H:%M") if appt.slot_end_time else None
    if start and end:
        return f"{start}-{end}"
    return start or end or ""
 
 
@api_view(["GET"])
@permission_classes([HasRolePermission])
def appointment_dashboard(request):
    """
    GET /appointment_dashboard/
    Optional query params: date=YYYY-MM-DD, status=Scheduled|Rescheduled|Cancelled,
    therapist_id=<employeeId>  (therapist_id filter only applies for admin/receptionist —
    a therapist caller is always scoped to their own appointments regardless).
 
    Role resolution (via Global db -> backend_diagnostics_profile, matched on
    employeeId == auth-user-id):
      - MDC-R-ADM or MDC-R-REC in primaryRole/additionalRoles -> full dashboard:
        every appointment, filterable by date/status/therapist, plus summary metrics.
      - MDC-R-PDC in primaryRole/additionalRoles -> therapist view, scoped to
        only their own appointments (as therapist_id or rescheduled_therapist_id).
        Granted purely on the role tag, so a therapist with no appointments yet
        still gets the dashboard (with zeroed-out counts) instead of a 403.
      - Otherwise, if this employeeId happens to appear as therapist_id or
        rescheduled_therapist_id on any existing appointment -> same therapist
        view (fallback for accounts without the MDC-R-PDC tag set).
      - Otherwise -> 403, no legitimate reason to see this dashboard.
    """
    employee_id = (
        request.data.get("auth-user-id")
       )
    if not employee_id:
        return Response({"success": False, "error": "'auth-user-id' is required."}, status=400)
 
    profile = profile_collection.find_one({"employeeId": employee_id})
    roles = _roles_for(profile)
    viewer_name = profile.get("employeeName") if profile else None
 
    is_admin = ADMIN_ROLE in roles
    is_receptionist = RECEPTIONIST_ROLE in roles
    is_therapist_role = THERAPIST_ROLE in roles
 
    # ---- resolve role + base scope (before date/status/therapist filters) ----
    if is_admin or is_receptionist:
        role = "admin" if is_admin else "receptionist"
        base_scope = AppointmentSchedule.objects.all()
    else:
        own_scope = Q(therapist_id=employee_id) | Q(rescheduled_therapist_id=employee_id)
        has_appointment_history = AppointmentSchedule.objects.filter(own_scope).exists()
        if not is_therapist_role and not has_appointment_history:
            return Response(
                {"success": False, "error": "You don't have access to the appointment dashboard."},
                status=403
            )
        role = "therapist"
        base_scope = AppointmentSchedule.objects.filter(own_scope)
 
    # ---- query params ---------------------------------------------------
    date_param = request.query_params.get("date")
    status_param = request.query_params.get("status")
    therapist_param = request.query_params.get("therapist_id")
 
    filters = Q()
    if date_param:
        try:
            parsed_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            return Response({"success": False, "error": "Invalid 'date' — expected YYYY-MM-DD."}, status=400)
        filters &= Q(date=parsed_date)
    if status_param:
        filters &= Q(status=status_param)
    if therapist_param and role in ("admin", "receptionist"):
        filters &= (Q(therapist_id=therapist_param) | Q(rescheduled_therapist_id=therapist_param))
        # NOTE: a "therapist" caller can't widen or redirect their scope via
        # this param — they only ever see base_scope (their own appointments).
 
    queryset = base_scope.filter(filters).order_by("-date", "slot_start_time")
 
    # ---- summary metrics --------------------------------------------------
    # total/scheduled/rescheduled/cancelled respect the selected date filter
    # (so picking a date updates these counts to that day's breakdown) while
    # ignoring status/therapist filters, so switching those doesn't skew the
    # picture. today_appointments always reflects the literal current date,
    # regardless of what's selected in the date filter.
    today = date_cls.today()
    summary_scope = base_scope.filter(date=parsed_date) if date_param else base_scope
    summary = {
        "total_appointments": summary_scope.count(),
        "today_appointments": base_scope.filter(date=today).count(),
        "scheduled_appointments": summary_scope.filter(status="Scheduled").count(),
        "rescheduled_appointments": summary_scope.filter(status="Rescheduled").count(),
        "cancelled": summary_scope.filter(status="Cancelled").count(),
    }
 
    # ---- resolve therapist names in one bulk Mongo round-trip -------------
    therapist_ids = set()
    for a in queryset:
        if a.therapist_id:
            therapist_ids.add(a.therapist_id)
        if a.rescheduled_therapist_id:
            therapist_ids.add(a.rescheduled_therapist_id)
 
    name_map = {}
    if therapist_ids:
        for p in profile_collection.find(
            {"employeeId": {"$in": list(therapist_ids)}},
            {"employeeId": 1, "employeeName": 1},
        ):
            name_map[p.get("employeeId")] = p.get("employeeName")
 
    data = []
    for a in queryset:
        # Effective therapist = who currently holds the slot: therapist_id
        # unless it's been reassigned, in which case rescheduled_therapist_id.
        effective_id = (
            a.rescheduled_therapist_id
            if a.status == "Rescheduled" and a.rescheduled_therapist_id
            else a.therapist_id
        )
        data.append({
            "appointment_id": a.appointment_id,
            "registration_number": a.registration_number,
            "date": a.date.isoformat() if a.date else None,
            "name_of_child": a.name_of_child,
            "therapist_id": effective_id,
            "therapist_name": name_map.get(effective_id, effective_id),
            "original_therapist_id": a.therapist_id,
            "original_therapist_name": name_map.get(a.therapist_id, a.therapist_id),
            "slot_time": _format_slot_time(a),
            "status": a.status,
        })
 
    return Response({
        "success": True,
        "role": role,
        "viewer": {"employee_id": employee_id, "employee_name": viewer_name},
        "summary": summary,
        "data": data,
    })

#########################
#     Enquiry form      #
#########################

@api_view(['GET', 'POST'])
@permission_classes([HasRolePermission])
def enquiryform(request):
    """
    GET  -> list all enquiries, most recent first
    POST -> create a new enquiry from the "+" Enquiry Form modal
    """
    if request.method == 'GET':
        enquiries = EnquiryForm.objects.order_by('-enquiry_id')
        serializer = EnquiryFormSerializer(enquiries, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

    # POST
    # auth-user-id normally arrives as a header via apiRequest's auto-injection,
    # but also check request.data in case it's sent in the body — covers both.
    employee_id = (
        request.data.get('auth-user-id')
        or request.headers.get('auth-user-id')
        or request.META.get('HTTP_AUTH_USER_ID')
    )

    serializer = EnquiryFormSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(created_by=employee_id)
        return Response(
            {
                "message": f"Enquiry saved for {serializer.instance.name_of_child}.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )
    return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
@permission_classes([HasRolePermission])
def search_appointments(request):
    """
    GET /search_appointments/?q=<search term>
    Searches Scheduled/Rescheduled appointments by child name or mobile number
    """
    q = request.query_params.get('q', '').strip()
    
    # Exclude appointments that have already been registered
    registered_ids = Registration.objects.filter(appointment_id__isnull=False).values_list('appointment_id', flat=True)
    qs = AppointmentSchedule.objects.filter(status__in=["Scheduled", "Rescheduled"]).exclude(appointment_id__in=list(registered_ids))
    
    if q:
        qs = qs.filter(
            Q(name_of_child__icontains=q) | 
            Q(mobile_number__icontains=q) |
            Q(father_name__icontains=q) |
            Q(mother_name__icontains=q)
        )
    qs = qs.order_by('-date')[:50]
    serializer = AppointmentScheduleSerializer(qs, many=True)
    return Response(serializer.data)