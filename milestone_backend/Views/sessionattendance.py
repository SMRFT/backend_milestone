from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import connection
from datetime import datetime
import json

from ..models import DailyTimeSlot, PatientSessionAttendance, Registration, TherapyDetails
from ..serializers import DailyTimeSlotSerializer, PatientSessionAttendanceSerializer
from pyauth.auth import HasRolePermission


@api_view(['GET'])
def load_session_attendance(request):
    try:
        registration_number = request.GET.get('registration_number')
        date_str = request.GET.get('attendance_date')

        if not registration_number or not date_str:
            return Response(
                {"error": "registration_number and attendance_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get start and end of the month for the date_obj
        date_start_month = datetime(date_obj.year, date_obj.month, 1, 0, 0, 0)
        import calendar
        _, last_day = calendar.monthrange(date_obj.year, date_obj.month)
        date_end_month = datetime(date_obj.year, date_obj.month, last_day, 23, 59, 59)

        # 1. Fetch PatientAttendance record for registration_number in this month using raw PyMongo
        db = connection.cursor().db.connection
        collection = db['milestone_backend_patientattendance']

        attendance_doc = collection.find_one({
            "registration_number": registration_number,
            "attendance_date": {
                "$gte": date_start_month,
                "$lte": date_end_month
            },
            "is_active": True
        }, sort=[("attendance_date", -1)])

        if not attendance_doc:
            return Response({
                "status": "error",
                "message": "No attendance record found for this patient in this month.",
                "data": []
            }, status=status.HTTP_404_NOT_FOUND)

        # Parse therapy_details from attendance
        therapy_details_raw = attendance_doc.get("therapy_details")
        if isinstance(therapy_details_raw, str):
            try:
                therapy_details = json.loads(therapy_details_raw)
            except:
                therapy_details = []
        elif isinstance(therapy_details_raw, list):
            therapy_details = therapy_details_raw
        else:
            therapy_details = []

        # 2. Fetch all active DailyTimeSlots
        all_slots = DailyTimeSlot.objects.all()
        active_slots = [s for s in all_slots if s.is_active]
        active_slots.sort(key=lambda s: s.sequence)
        slots_data = DailyTimeSlotSerializer(active_slots, many=True).data

        # 3. Fetch all TherapyDetails for mapping name -> id using ORM
        therapies_list = TherapyDetails.objects.all()
        therapy_map = {t.therapy_name: t.therapy_id for t in therapies_list}

        # 4. Fetch existing PatientSessionAttendance records for this exact date
        existing_records_qs = PatientSessionAttendance.objects.filter(
            registration_number=registration_number,
            attendance_date=date_obj
        )
        existing_records = [r for r in existing_records_qs if r.is_active]

        existing_map = {}
        for r in existing_records:
            existing_map[r.therapy_id] = r

        # 5. Build list of therapies with current/default state
        result_therapies = []
        for t in therapy_details:
            if not isinstance(t, dict):
                continue
            name = t.get("therapy_name")
            tid = therapy_map.get(name) or t.get("therapy_type") or ""
            
            existing = existing_map.get(tid)
            
            if existing:
                attended = True
                attended_slot = existing.attended_slot
                slot_label = existing.slot_label
                therapist = existing.therapist or ""
                sessions_attended = existing.sessions_attended
            else:
                attended = False
                attended_slot = slots_data[0]["slot_id"] if slots_data else ""
                slot_label = slots_data[0]["label"] if slots_data else ""
                therapist = ""
                sessions_attended = 1

            result_therapies.append({
                "therapy_id": tid,
                "therapy_name": name,
                "attended": attended,
                "attended_slot": attended_slot,
                "slot_label": slot_label,
                "therapist": therapist,
                "sessions_attended": sessions_attended
            })

        return Response({
            "status": "success",
            "therapies": result_therapies,
            "slots": slots_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        import traceback
        print("Error in load_session_attendance:", traceback.format_exc())
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def save_session_attendance(request):
    try:
        data = request.data
        employee_id = data.get("auth-user-id")
        registration_number = data.get('registration_number')
        date_str = data.get('attendance_date')
        checked_therapies = data.get('checked_therapies', [])
        all_therapies = data.get('all_therapies', [])

        if not registration_number or not date_str:
            return Response(
                {"error": "registration_number and attendance_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get start and end of the month for date_obj
        date_start_month = datetime(date_obj.year, date_obj.month, 1, 0, 0, 0)
        import calendar
        _, last_day = calendar.monthrange(date_obj.year, date_obj.month)
        date_end_month = datetime(date_obj.year, date_obj.month, last_day, 23, 59, 59)

        db = connection.cursor().db.connection
        collection = db['milestone_backend_patientattendance']

        # 1. Find the PatientAttendance record for the month using PyMongo
        attendance_doc = collection.find_one({
            "registration_number": registration_number,
            "attendance_date": {
                "$gte": date_start_month,
                "$lte": date_end_month
            },
            "is_active": True
        }, sort=[("attendance_date", -1)])

        if not attendance_doc:
            return Response(
                {"error": "No PatientAttendance record found for this patient in this month."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Save PatientSessionAttendance for this exact date using ORM
        # Delete existing entries for this patient on this exact date
        PatientSessionAttendance.objects.filter(
            registration_number=registration_number,
            attendance_date=date_obj
        ).delete()

        # Insert new ones for checked therapies on this exact date
        for ct in checked_therapies:
            PatientSessionAttendance.objects.create(
                registration_number=registration_number,
                attendance_date=date_obj,
                therapy_id=ct.get("therapy_id"),
                therapy_name=ct.get("therapy_name"),
                attended_slot=ct.get("attended_slot"),
                slot_label=ct.get("slot_label"),
                therapist=ct.get("therapist", ""),
                sessions_attended=int(ct.get("sessions_attended", 1)),
                created_by=employee_id,
                created_date=timezone.now(),
                is_active=True
            )

        # 3. Query all PatientSessionAttendance records for this patient in the entire month
        all_month_sessions_qs = PatientSessionAttendance.objects.filter(
            registration_number=registration_number,
            attendance_date__range=(date_start_month.date(), date_end_month.date())
        )
        all_month_sessions = [r for r in all_month_sessions_qs if r.is_active]

        monthly_sessions_map = {}
        for r in all_month_sessions:
            tid = r.therapy_id
            sess = int(r.sessions_attended or 1)
            monthly_sessions_map[tid] = monthly_sessions_map.get(tid, 0) + sess

        # 4. Update the monthly PatientAttendance record
        curr_details_raw = attendance_doc.get("therapy_details")
        if isinstance(curr_details_raw, str):
            try:
                curr_details = json.loads(curr_details_raw)
            except:
                curr_details = []
        elif isinstance(curr_details_raw, list):
            curr_details = curr_details_raw
        else:
            curr_details = []

        therapies_list = TherapyDetails.objects.all()
        therapy_map = {t.therapy_name: t.therapy_id for t in therapies_list}

        updated_details = []
        for t in curr_details:
            if not isinstance(t, dict):
                continue
            name = t.get("therapy_name")
            tid = t.get("therapy_id") or t.get("therapy_type") or ""
            if not tid:
                tid = therapy_map.get(name) or ""
            
            monthly_sum = monthly_sessions_map.get(tid, 0)
            
            t["therapy_id"] = tid
            t["sessions_attended"] = monthly_sum
            t["no_of_sessions_attended"] = monthly_sum
            t["total_no_of_session_attended"] = monthly_sum
            updated_details.append(t)

        if isinstance(curr_details_raw, str):
            updated_details_val = json.dumps(updated_details)
        else:
            updated_details_val = updated_details

        collection.update_one(
            {"_id": attendance_doc["_id"]},
            {"$set": {
                "therapy_details": updated_details_val,
                "lastmodified_by": employee_id,
                "lastmodified_date": datetime.now()
            }}
        )

        return Response({
            "status": "success",
            "message": "Session attendance saved successfully."
        }, status=status.HTTP_200_OK)

    except Exception as e:
        import traceback
        print("Error in save_session_attendance:", traceback.format_exc())
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_active_slots(request):
    try:
        all_slots = DailyTimeSlot.objects.all()
        active_slots = [s for s in all_slots if s.is_active]
        active_slots.sort(key=lambda s: s.sequence)
        slots_data = DailyTimeSlotSerializer(active_slots, many=True).data
        return Response({
            "status": "success",
            "data": slots_data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_underattended_patients(request):
    try:
        month_str = request.GET.get('month')
        year_str = request.GET.get('year')
        
        try:
            month = int(month_str) if month_str else datetime.now().month
            year = int(year_str) if year_str else datetime.now().year
        except ValueError:
            return Response(
                {"error": "Invalid month or year parameter"},
                status=status.HTTP_400_BAD_REQUEST
            )

        import calendar
        _, last_day = calendar.monthrange(year, month)
        start_datetime = datetime(year, month, 1, 0, 0, 0)
        end_datetime = datetime(year, month, last_day, 23, 59, 59)

        db = connection.cursor().db.connection
        collection = db['milestone_backend_patientattendance']

        # 1. Fetch all PatientAttendance records for this month using PyMongo
        attendance_cursor = collection.find({
            "attendance_date": {
                "$gte": start_datetime,
                "$lte": end_datetime
            },
            "is_active": True
        })

        # 2. Fetch all PatientSessionAttendance records for this month using ORM
        session_records_qs = PatientSessionAttendance.objects.filter(
            attendance_date__range=(start_datetime.date(), end_datetime.date())
        )
        session_records = [r for r in session_records_qs if r.is_active]

        # Map: (reg_num, therapy_name) -> total sessions from session attendance
        session_attended_map = {}
        for r in session_records:
            reg = r.registration_number
            tname = r.therapy_name
            sess = int(r.sessions_attended or 1)
            key = (reg, tname)
            session_attended_map[key] = session_attended_map.get(key, 0) + sess

        # Group daily attendance records by patient
        patient_therapies = {}
        for att in attendance_cursor:
            reg = att.get("registration_number")
            t_details_raw = att.get("therapy_details")
            if isinstance(t_details_raw, str):
                try:
                    t_details = json.loads(t_details_raw)
                except:
                    t_details = []
            elif isinstance(t_details_raw, list):
                t_details = t_details_raw
            else:
                t_details = []
            
            if not isinstance(t_details, list):
                continue

            if reg not in patient_therapies:
                patient_therapies[reg] = {}

            for t in t_details:
                if not isinstance(t, dict):
                    continue
                name = t.get("therapy_name")
                tid = t.get("therapy_id") or t.get("therapy_type") or ""
                scheduled = int(t.get("sesion_per_therapy") or t.get("sessions_per_month") or 0)
                
                # Check for daily recorded sessions attended
                daily_sess = int(t.get("total_no_of_session_attended") or t.get("sessions_attended") or 0)

                if name not in patient_therapies[reg]:
                    patient_therapies[reg][name] = {
                        "scheduled": scheduled,
                        "daily_attended": 0,
                        "presence_count": 0,
                        "therapy_id": tid
                    }
                
                if scheduled > patient_therapies[reg][name]["scheduled"]:
                    patient_therapies[reg][name]["scheduled"] = scheduled
                
                patient_therapies[reg][name]["daily_attended"] += daily_sess
                patient_therapies[reg][name]["presence_count"] += 1
                if tid and not patient_therapies[reg][name]["therapy_id"]:
                    patient_therapies[reg][name]["therapy_id"] = tid

        # 3. Fetch patient details (names and dob)
        reg_numbers = list(patient_therapies.keys())
        registrations = Registration.objects.filter(registration_number__in=reg_numbers)
        patient_names = {r.registration_number: r.name_of_child for r in registrations}
        patient_dobs = {r.registration_number: (r.dob.strftime('%Y-%m-%d') if r.dob else "N/A") for r in registrations}

        result = []
        for reg, therapies_dict in patient_therapies.items():
            patient_name = patient_names.get(reg, "Unknown Patient")
            dob = patient_dobs.get(reg, "N/A")
            
            underattended_therapies = []
            for tname, data in therapies_dict.items():
                scheduled = data["scheduled"]
                
                key = (reg, tname)
                if key in session_attended_map:
                    attended = session_attended_map[key]
                elif data["daily_attended"] > 0:
                    attended = data["daily_attended"]
                else:
                    attended = data["presence_count"]

                if scheduled > attended:
                    underattended_therapies.append({
                        "therapy_id": data["therapy_id"],
                        "therapy_name": tname,
                        "scheduled_sessions": scheduled,
                        "attended_sessions": attended,
                        "pending_sessions": scheduled - attended
                    })

            if underattended_therapies:
                result.append({
                    "registration_number": reg,
                    "patient_name": patient_name,
                    "dob": dob,
                    "underattended_therapies": underattended_therapies
                })

        return Response({
            "status": "success",
            "month": month,
            "year": year,
            "data": result
        }, status=status.HTTP_200_OK)

    except Exception as e:
        import traceback
        print("Error in get_underattended_patients:", traceback.format_exc())
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_monthly_attendance_report(request):
    try:
        month_str = request.GET.get('month')
        year_str = request.GET.get('year')
        
        try:
            month = int(month_str) if month_str else datetime.now().month
            year = int(year_str) if year_str else datetime.now().year
        except ValueError:
            return Response(
                {"error": "Invalid month or year parameter"},
                status=status.HTTP_400_BAD_REQUEST
            )

        import calendar
        _, last_day = calendar.monthrange(year, month)
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, last_day).date()

        # Fetch PatientSessionAttendance records
        records_qs = PatientSessionAttendance.objects.filter(
            attendance_date__range=(start_date, end_date)
        )
        records = [r for r in records_qs if r.is_active]

        # Get registration numbers and their names
        reg_numbers = list(set(r.registration_number for r in records))
        registrations = Registration.objects.filter(registration_number__in=reg_numbers)
        patient_names = {r.registration_number: r.name_of_child for r in registrations}

        # Get consulting doctors to map therapist employee_id to name
        from milestone_backend.models import ConsultingDoctor
        doctors = ConsultingDoctor.objects.all()
        doctor_map = {}
        for d in doctors:
            emp_id = getattr(d, 'employee_id', None)
            doc_name = getattr(d, 'name', None)
            if emp_id and doc_name:
                doctor_map[emp_id] = doc_name

        matrix_data = {}
        for r in records:
            reg = r.registration_number
            tname = r.therapy_name
            day = r.attendance_date.day
            slot = r.slot_label or r.attended_slot or ""
            therapist_id = r.therapist or ""
            therapist_name = doctor_map.get(therapist_id, therapist_id)
            
            key = (reg, tname)
            if key not in matrix_data:
                matrix_data[key] = {
                    "registration_number": reg,
                    "patient_name": patient_names.get(reg, "Unknown Patient"),
                    "therapy_name": tname,
                    "days": {}
                }
            
            day_str = str(day)
            if day_str not in matrix_data[key]["days"]:
                matrix_data[key]["days"][day_str] = []
            
            matrix_data[key]["days"][day_str].append({
                "slot": slot,
                "therapist": therapist_name
            })

        result = list(matrix_data.values())
        return Response({
            "status": "success",
            "month": month,
            "year": year,
            "last_day": last_day,
            "data": result
        }, status=status.HTTP_200_OK)

    except Exception as e:
        import traceback
        print("Error in get_monthly_attendance_report:", traceback.format_exc())
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

