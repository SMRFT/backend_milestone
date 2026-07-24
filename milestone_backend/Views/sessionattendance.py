from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import connection
from datetime import date, datetime
import json

from ..models import DailyTimeSlot, PatientSessionAttendance, Registration, TherapyDetails
from ..serializers import DailyTimeSlotSerializer, PatientSessionAttendanceSerializer
from pyauth.auth import HasRolePermission


@api_view(['GET'])
@permission_classes([HasRolePermission])
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

        has_monthly_attendance = bool(attendance_doc)

        # Parse therapy_details from attendance if exists
        total_planned_sessions = 0
        if attendance_doc:
            try:
                total_planned_sessions = int(attendance_doc.get("session") or 0)
            except:
                total_planned_sessions = 0

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

            sum_planned = sum(
                int(t.get("sesion_per_therapy") or t.get("sessions_per_month") or 0)
                for t in therapy_details
                if isinstance(t, dict)
            )
            if sum_planned > total_planned_sessions:
                total_planned_sessions = sum_planned

        # Fetch sessions for other days in this month to calculate total projected sessions
        other_days_sessions = PatientSessionAttendance.objects.filter(
            registration_number=registration_number,
            attendance_date__range=(date_start_month.date(), date_end_month.date())
        ).exclude(attendance_date=date_obj)

        other_days_total = sum(int(r.sessions_attended or 1) for r in other_days_sessions if r.is_active)

        # 2. Fetch all active DailyTimeSlots
        all_slots = DailyTimeSlot.objects.all()
        active_slots = [s for s in all_slots if s.is_active]
        active_slots.sort(key=lambda s: s.sequence)
        slots_data = DailyTimeSlotSerializer(active_slots, many=True).data

        # 3. Fetch all TherapyDetails for mapping name -> id using ORM
        therapies_list = TherapyDetails.objects.all()

        # Fetch consulting doctors to map therapist name <-> ID
        from milestone_backend.models import ConsultingDoctor
        doctors_qs = ConsultingDoctor.objects.all()
        id_to_name = {}
        name_to_id = {}
        for d in doctors_qs:
            emp_id = str(getattr(d, 'employee_id', '') or '').strip()
            doc_name = str(getattr(d, 'name', '') or '').strip()
            if emp_id and doc_name:
                id_to_name[emp_id] = doc_name
                name_to_id[doc_name] = emp_id

        # 4. Fetch existing PatientSessionAttendance records for this exact date
        existing_records_qs = PatientSessionAttendance.objects.filter(
            registration_number=registration_number,
            attendance_date=date_obj
        )
        existing_records = [r for r in existing_records_qs if r.is_active]

        existing_map = {r.therapy_id: r for r in existing_records}

        # 5. Fetch all PatientSessionAttendance records in this month to compute monthly totals so far
        all_month_sessions_qs = PatientSessionAttendance.objects.filter(
            registration_number=registration_number,
            attendance_date__range=(date_start_month.date(), date_end_month.date())
        )
        month_totals_map = {}
        for r in all_month_sessions_qs:
            if r.is_active:
                month_totals_map[r.therapy_id] = month_totals_map.get(r.therapy_id, 0) + int(r.sessions_attended or 1)

        # 6. Build list of therapies with current/default state out of all available therapies
        result_therapies = []
        for t in therapies_list:
            name = t.therapy_name
            tid = t.therapy_id
            
            existing = existing_map.get(tid)
            
            if existing:
                attended = True
                attended_slot = existing.attended_slot
                slot_label = existing.slot_label
                raw_t = existing.therapist_id or existing.therapist or ""
                # Prefer employee_id for the dropdown value
                therapist = existing.therapist_id or name_to_id.get(existing.therapist) or existing.therapist or ""
                sessions_attended = existing.sessions_attended
                session_id = existing.session_id or ""
            else:
                attended = False
                attended_slot = slots_data[0]["slot_id"] if slots_data else ""
                slot_label = slots_data[0]["label"] if slots_data else ""
                therapist = ""
                sessions_attended = 1
                session_id = ""

            result_therapies.append({
                "therapy_id": tid,
                "therapy_name": name,
                "attended": attended,
                "attended_slot": attended_slot,
                "slot_label": slot_label,
                "therapist": therapist,
                "sessions_attended": sessions_attended,
                "session_id": session_id,
                "max_allowed_sessions": total_planned_sessions,
                "month_total_sessions": month_totals_map.get(tid, 0)
            })

        return Response({
            "status": "success",
            "has_monthly_attendance": has_monthly_attendance,
            "total_planned_sessions": total_planned_sessions,
            "other_days_total": other_days_total,
            "therapies": result_therapies,
            "slots": slots_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        import traceback
        print("Error in load_session_attendance:", traceback.format_exc())
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasRolePermission])
def save_session_attendance(request):
    try:
        data = request.data
        employee_id = data.get("auth-user-id", "system")

        registration_number = data.get('registration_number')
        date_str = data.get('attendance_date')
        checked_therapies = data.get('checked_therapies', [])
        all_therapies = data.get('all_therapies', [])

        if not registration_number or not date_str:
            return Response(
                {"error": "registration_number and attendance_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        for ct in checked_therapies:
            if not ct.get("therapist"):
                return Response(
                    {"error": f"Therapist is required for therapy: {ct.get('therapy_name', 'Unknown')}"},
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

        therapies_list = TherapyDetails.objects.all()
        therapy_map = {t.therapy_name: t.therapy_id for t in therapies_list}

        # Calculate total planned sessions in monthly attendance doc
        total_planned_sessions = 0
        if attendance_doc:
            try:
                total_planned_sessions = int(attendance_doc.get("session") or 0)
            except:
                total_planned_sessions = 0

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

            sum_details_sessions = sum(
                int(item.get("sesion_per_therapy") or item.get("sessions_per_month") or 0)
                for item in curr_details
                if isinstance(item, dict)
            )
            if sum_details_sessions > total_planned_sessions:
                total_planned_sessions = sum_details_sessions

        # Fetch sessions for other days in this month to calculate total projected sessions
        other_days_sessions = PatientSessionAttendance.objects.filter(
            registration_number=registration_number,
            attendance_date__range=(date_start_month.date(), date_end_month.date())
        ).exclude(attendance_date=date_obj)

        other_days_total = sum(int(r.sessions_attended or 1) for r in other_days_sessions if r.is_active)
        new_day_total = sum(int(ct.get("sessions_attended", 1)) for ct in checked_therapies)
        total_projected = other_days_total + new_day_total

        # Validate overall total against monthly limit if monthly attendance exists
        if attendance_doc and total_planned_sessions > 0:
            if total_projected > total_planned_sessions:
                return Response(
                    {"error": f"Cannot add sessions: total sessions for this month ({total_projected}) would exceed the total limit of {total_planned_sessions} sessions set in monthly attendance."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 2. Save PatientSessionAttendance for this exact date using ORM
        existing_sessions = PatientSessionAttendance.objects.filter(
            registration_number=registration_number,
            attendance_date=date_obj
        )
        existing_session_map = {r.therapy_id: r for r in existing_sessions}
        
        # Delete existing entries for this date
        existing_sessions.delete()

        # Fetch consulting doctors to map therapist name <-> ID
        from milestone_backend.models import ConsultingDoctor
        doctors_qs = ConsultingDoctor.objects.all()
        id_to_name = {}
        name_to_id = {}
        for d in doctors_qs:
            emp_id = str(getattr(d, 'employee_id', '') or '').strip()
            doc_name = str(getattr(d, 'name', '') or '').strip()
            if emp_id and doc_name:
                id_to_name[emp_id] = doc_name
                name_to_id[doc_name] = emp_id

        # Insert new ones for checked therapies on this exact date
        for ct in checked_therapies:
            tid = ct.get("therapy_id")
            existing_rec = existing_session_map.get(tid)
            preserved_session_id = existing_rec.session_id if existing_rec else None
            preserved_is_confirmed = existing_rec.is_confirmed if existing_rec else False
            preserved_confirmed_by = existing_rec.confirmed_by if existing_rec else ""
            preserved_confirmed_date = existing_rec.confirmed_date if existing_rec else None

            raw_therapist = str(ct.get("therapist", "")).strip()
            raw_therapist_id = str(ct.get("therapist_id", "")).strip() or raw_therapist

            # Determine therapist name and therapist ID cleanly
            if raw_therapist in id_to_name:
                t_id = raw_therapist
                t_name = id_to_name[raw_therapist]
            elif raw_therapist in name_to_id:
                t_id = name_to_id[raw_therapist]
                t_name = raw_therapist
            elif raw_therapist_id in id_to_name:
                t_id = raw_therapist_id
                t_name = id_to_name[raw_therapist_id]
            else:
                t_id = raw_therapist_id
                t_name = raw_therapist

            PatientSessionAttendance.objects.create(
                registration_number=registration_number,
                attendance_date=date_obj,
                therapy_id=tid,
                therapy_name=ct.get("therapy_name"),
                attended_slot=ct.get("attended_slot"),
                slot_label=ct.get("slot_label"),
                therapist=t_name,
                therapist_id=t_id,
                is_confirmed=preserved_is_confirmed,
                confirmed_by=preserved_confirmed_by,
                confirmed_date=preserved_confirmed_date,
                sessions_attended=int(ct.get("sessions_attended", 1)),
                session_id=preserved_session_id,
                created_by=employee_id,
                created_date=timezone.now(),
                is_active=True
            )

        # 3. If attendance_doc exists, update monthly PatientAttendance record
        if attendance_doc:
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

        db = connection.cursor().db.connection
        collection = db['milestone_backend_patientattendance']

        # 1. Fetch all PatientAttendance records using PyMongo and filter by target month/year in Python
        attendance_cursor = list(collection.find({
            "$or": [
                {"is_active": True},
                {"is_active": {"$exists": False}}
            ]
        }))

        patient_planned_therapies = {}
        for att in attendance_cursor:
            att_date = att.get("attendance_date")
            rec_year, rec_month = None, None
            if isinstance(att_date, datetime):
                rec_year, rec_month = att_date.year, att_date.month
            elif isinstance(att_date, date):
                rec_year, rec_month = att_date.year, att_date.month
            elif isinstance(att_date, str):
                try:
                    parsed_dt = datetime.strptime(att_date[:10], '%Y-%m-%d')
                    rec_year, rec_month = parsed_dt.year, parsed_dt.month
                except:
                    continue

            if rec_year != year or rec_month != month:
                continue

            reg = str(att.get("registration_number", "")).strip()
            if not reg:
                continue

            if reg not in patient_planned_therapies:
                patient_planned_therapies[reg] = {}

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

            if isinstance(t_details, list):
                for t in t_details:
                    if isinstance(t, dict):
                        tname = t.get("therapy_name")
                        tid = t.get("therapy_id") or t.get("therapy_type") or ""
                        sched = int(t.get("sesion_per_therapy") or t.get("sessions_per_month") or 0)
                        if tname:
                            patient_planned_therapies[reg][tname] = {
                                "scheduled": sched,
                                "therapy_id": tid
                            }

        # 2. Fetch all PatientSessionAttendance records for target month/year
        session_records_qs = PatientSessionAttendance.objects.all()
        session_attended_map = {}
        for r in session_records_qs:
            if not r.is_active:
                continue
            att_d = r.attendance_date
            if not att_d:
                continue
            if att_d.year == year and att_d.month == month:
                reg = str(r.registration_number or "").strip()
                tname = r.therapy_name
                sess = int(r.sessions_attended or 1)
                key = (reg, tname)
                session_attended_map[key] = session_attended_map.get(key, 0) + sess

        # 3. Fetch ALL registered patients
        all_registrations = list(Registration.objects.all().order_by('name_of_child'))

        result = []
        for r in all_registrations:
            reg = str(r.registration_number or "").strip()
            if not reg:
                continue
            patient_name = r.name_of_child or "Unknown Patient"
            
            if r.dob:
                if isinstance(r.dob, str):
                    dob = r.dob[:10]
                else:
                    dob = r.dob.strftime('%Y-%m-%d')
            else:
                dob = "N/A"
            
            planned_map = patient_planned_therapies.get(reg, {})
            
            # Combine all therapy names for this child (either planned in monthly attendance or logged in session attendance)
            all_therapies_for_child = set(planned_map.keys())
            for (s_reg, s_tname) in session_attended_map.keys():
                if s_reg == reg and s_tname:
                    all_therapies_for_child.add(s_tname)

            underattended_therapies = []
            for tname in sorted(all_therapies_for_child):
                planned_info = planned_map.get(tname, {})
                scheduled = planned_info.get("scheduled", 0)
                tid = planned_info.get("therapy_id", "")
                attended = session_attended_map.get((reg, tname), 0)

                underattended_therapies.append({
                    "therapy_id": tid,
                    "therapy_name": tname,
                    "scheduled_sessions": scheduled,
                    "attended_sessions": attended,
                    "pending_sessions": max(0, scheduled - attended)
                })

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

        # Get consulting doctors to map therapist employee_id <-> name
        from milestone_backend.models import ConsultingDoctor
        doctors = ConsultingDoctor.objects.all()
        id_to_name = {}
        name_to_id = {}
        for d in doctors:
            emp_id = str(getattr(d, 'employee_id', '') or '').strip()
            doc_name = str(getattr(d, 'name', '') or '').strip()
            if emp_id and doc_name:
                id_to_name[emp_id] = doc_name
                name_to_id[doc_name] = emp_id

        matrix_data = {}
        for r in records:
            reg = r.registration_number
            tname = r.therapy_name
            day = r.attendance_date.day
            slot = r.slot_label or r.attended_slot or ""
            
            raw_tid = str(getattr(r, 'therapist_id', '') or '').strip()
            raw_tname = str(r.therapist or '').strip()
            
            resolved_name = (
                id_to_name.get(raw_tname) or
                id_to_name.get(raw_tid) or
                (raw_tname if raw_tname and raw_tname not in id_to_name else None) or
                raw_tid
            )

            resolved_id = (
                raw_tid or
                name_to_id.get(raw_tname) or
                raw_tname
            )
            
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
                "therapist": resolved_name,
                "therapist_id": resolved_id,
                "session_id": r.session_id or "",
                "is_confirmed": bool(r.is_confirmed),
                "confirmed_by": r.confirmed_by or "",
                "confirmed_date": r.confirmed_date.strftime('%Y-%m-%d %H:%M') if r.confirmed_date else ""
            })

        result = list(matrix_data.values())
        result.sort(key=lambda x: (
            str(x.get("patient_name", "")).lower(),
            str(x.get("registration_number", "")).lower(),
            str(x.get("therapy_name", "")).lower()
        ))

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


@api_view(['POST', 'PATCH'])
def confirm_session_attendance(request):
    try:
        session_id = request.data.get('session_id')
        session_ids = request.data.get('session_ids', [])
        if session_id and session_id not in session_ids:
            session_ids.append(session_id)
            
        employee_id = request.data.get('employee_id', '') or request.headers.get('employee_id', '')

        if not session_ids:
            return Response({"status": "error", "message": "No session_id provided"}, status=status.HTTP_400_BAD_REQUEST)

        now_time = timezone.now()
        updated_count = PatientSessionAttendance.objects.filter(
            session_id__in=session_ids
        ).update(
            is_confirmed=True,
            confirmed_by=employee_id,
            confirmed_date=now_time
        )

        return Response({
            "status": "success",
            "message": f"{updated_count} session(s) confirmed successfully.",
            "confirmed_ids": session_ids
        }, status=status.HTTP_200_OK)
    except Exception as e:
        import traceback
        print("Error in confirm_session_attendance:", traceback.format_exc())
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

