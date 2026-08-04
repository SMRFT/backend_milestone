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


def safe_json_parse(data):
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            return parsed if isinstance(parsed, list) else []
        except:
            return []
    elif isinstance(data, list):
        return data
    return []



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

        if not attendance_doc:
            attendance_doc = collection.find_one({
                "registration_number": registration_number,
                "is_active": True
            }, sort=[("attendance_date", -1)])

        has_monthly_attendance = bool(attendance_doc)

        # Parse therapy_details, extra_attending_details, not_attending_details from attendance if exists
        total_planned_sessions = 0
        if attendance_doc:
            try:
                total_planned_sessions = int(attendance_doc.get("session") or 0)
            except:
                total_planned_sessions = 0

            therapy_details = safe_json_parse(attendance_doc.get("therapy_details"))
            extra_details = safe_json_parse(attendance_doc.get("extra_attending_details"))
            not_details = safe_json_parse(attendance_doc.get("not_attending_details"))

            total_extra = sum(int(x.get("sessions") or 0) for x in extra_details if isinstance(x, dict))
            total_not = sum(int(n.get("sessions") or 0) for n in not_details if isinstance(n, dict))

            total_planned_sessions = max(0, total_planned_sessions - total_not + total_extra)

            t_planned_map = {}
            for t in therapy_details:
                if isinstance(t, dict):
                    tname = t.get("therapy_name")
                    sched = int(t.get("sesion_per_therapy") or t.get("sessions_per_month") or 0)
                    if tname:
                        t_planned_map[tname] = sched

            for x in extra_details:
                if isinstance(x, dict):
                    xname = x.get("therapy_name")
                    xsessions = int(x.get("sessions") or 0)
                    if xname:
                        t_planned_map[xname] = t_planned_map.get(xname, 0) + xsessions

            for n in not_details:
                if isinstance(n, dict):
                    nname = n.get("therapy_name")
                    nsessions = int(n.get("sessions") or 0)
                    if nname:
                        t_planned_map[nname] = max(0, t_planned_map.get(nname, 0) - nsessions)

            sum_planned = sum(t_planned_map.values())
            if sum_planned > total_planned_sessions:
                total_planned_sessions = sum_planned

        # Fetch sessions for other days in this month to calculate total projected sessions
        all_patient_sessions = list(PatientSessionAttendance.objects.filter(registration_number=registration_number))
        
        other_days_sessions = [
            r for r in all_patient_sessions
            if r.is_active and r.attendance_date and parse_date_only(r.attendance_date) and parse_date_only(r.attendance_date).year == date_obj.year
            and parse_date_only(r.attendance_date).month == date_obj.month
            and parse_date_only(r.attendance_date) != date_obj
        ]

        other_days_total = sum(int(r.sessions_attended or 1) for r in other_days_sessions)

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

        from collections import defaultdict
        existing_map = defaultdict(list)
        for r in existing_records:
            existing_map[r.therapy_id].append(r)

        # 5. Fetch all PatientSessionAttendance records in this month to compute monthly totals so far
        all_month_sessions = [
            r for r in all_patient_sessions
            if r.is_active and r.attendance_date and parse_date_only(r.attendance_date) and parse_date_only(r.attendance_date).year == date_obj.year
            and parse_date_only(r.attendance_date).month == date_obj.month
        ]
        month_totals_map = {}
        for r in all_month_sessions:
            month_totals_map[r.therapy_id] = month_totals_map.get(r.therapy_id, 0) + int(r.sessions_attended or 1)

        slot_label_map = {s["slot_id"]: s["label"] for s in slots_data}

        # 6. Build list of therapies with current/default state out of all available therapies
        result_therapies = []
        for t in therapies_list:
            name = t.therapy_name
            tid = t.therapy_id
            
            recs = existing_map.get(tid, [])
            
            if recs:
                attended = True
                sessions_attended = sum(int(r.sessions_attended or 1) for r in recs)
                slots_info = []
                for r in recs:
                    t_val = r.therapist_id or name_to_id.get(r.therapist) or r.therapist or ""
                    s_label = r.slot_label or slot_label_map.get(r.attended_slot, "")
                    slots_info.append({
                        "attended_slot": r.attended_slot or (slots_data[0]["slot_id"] if slots_data else ""),
                        "slot_label": s_label,
                        "therapist": t_val,
                        "session_id": r.session_id or ""
                    })
                first_slot = slots_info[0]["attended_slot"]
                first_label = slots_info[0]["slot_label"]
                first_therapist = slots_info[0]["therapist"]
                first_session_id = slots_info[0]["session_id"]
            else:
                attended = False
                sessions_attended = 1
                default_slot = slots_data[0]["slot_id"] if slots_data else ""
                default_label = slots_data[0]["label"] if slots_data else ""
                slots_info = [{
                    "attended_slot": default_slot,
                    "slot_label": default_label,
                    "therapist": "",
                    "session_id": ""
                }]
                first_slot = default_slot
                first_label = default_label
                first_therapist = ""
                first_session_id = ""

            result_therapies.append({
                "therapy_id": tid,
                "therapy_name": name,
                "attended": attended,
                "attended_slot": first_slot,
                "slot_label": first_label,
                "therapist": first_therapist,
                "sessions_attended": sessions_attended,
                "session_id": first_session_id,
                "slots_info": slots_info,
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

        if not attendance_doc:
            attendance_doc = collection.find_one({
                "registration_number": registration_number,
                "is_active": True
            }, sort=[("attendance_date", -1)])

        therapies_list = TherapyDetails.objects.all()
        therapy_map = {t.therapy_name: t.therapy_id for t in therapies_list}

        # Calculate total planned sessions in monthly attendance doc (including extra and not-attending)
        total_planned_sessions = 0
        if attendance_doc:
            try:
                total_planned_sessions = int(attendance_doc.get("session") or 0)
            except:
                total_planned_sessions = 0

            curr_details = safe_json_parse(attendance_doc.get("therapy_details"))
            extra_details = safe_json_parse(attendance_doc.get("extra_attending_details"))
            not_details = safe_json_parse(attendance_doc.get("not_attending_details"))

            total_extra = sum(int(x.get("sessions") or 0) for x in extra_details if isinstance(x, dict))
            total_not = sum(int(n.get("sessions") or 0) for n in not_details if isinstance(n, dict))

            total_planned_sessions = max(0, total_planned_sessions - total_not + total_extra)

            t_planned_map = {}
            for t in curr_details:
                if isinstance(t, dict):
                    tname = t.get("therapy_name")
                    sched = int(t.get("sesion_per_therapy") or t.get("sessions_per_month") or 0)
                    if tname:
                        t_planned_map[tname] = sched

            for x in extra_details:
                if isinstance(x, dict):
                    xname = x.get("therapy_name")
                    xsessions = int(x.get("sessions") or 0)
                    if xname:
                        t_planned_map[xname] = t_planned_map.get(xname, 0) + xsessions

            for n in not_details:
                if isinstance(n, dict):
                    nname = n.get("therapy_name")
                    nsessions = int(n.get("sessions") or 0)
                    if nname:
                        t_planned_map[nname] = max(0, t_planned_map.get(nname, 0) - nsessions)

            sum_details_sessions = sum(t_planned_map.values())
            if sum_details_sessions > total_planned_sessions:
                total_planned_sessions = sum_details_sessions

        # Fetch sessions for other days in this month to calculate total projected sessions
        all_patient_sessions = list(PatientSessionAttendance.objects.filter(registration_number=registration_number))
        other_days_sessions = [
            r for r in all_patient_sessions
            if r.is_active and r.attendance_date and parse_date_only(r.attendance_date) and parse_date_only(r.attendance_date).year == date_obj.year
            and parse_date_only(r.attendance_date).month == date_obj.month
            and parse_date_only(r.attendance_date) != date_obj
        ]

        other_days_total = sum(int(r.sessions_attended or 1) for r in other_days_sessions)
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
        existing_session_map = {}
        for r in existing_sessions:
            if r.therapy_id not in existing_session_map:
                existing_session_map[r.therapy_id] = []
            existing_session_map[r.therapy_id].append(r)
        
        # Delete existing entries for this date
        existing_sessions.delete()

        # Fetch active slots for label lookup
        all_slots_qs = DailyTimeSlot.objects.all()
        slot_label_lookup = {s.slot_id: s.label for s in all_slots_qs}

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
            existing_recs = existing_session_map.get(tid, [])
            
            slots_info = ct.get("slots_info")
            if not slots_info or not isinstance(slots_info, list) or len(slots_info) == 0:
                slots_info = [{
                    "attended_slot": ct.get("attended_slot"),
                    "slot_label": ct.get("slot_label"),
                    "therapist": ct.get("therapist"),
                    "therapist_id": ct.get("therapist_id") or ct.get("therapist"),
                    "session_id": ct.get("session_id")
                }]

            for s_idx, s_item in enumerate(slots_info):
                matching_existing = existing_recs[s_idx] if s_idx < len(existing_recs) else None
                preserved_session_id = s_item.get("session_id") or (matching_existing.session_id if matching_existing else None)
                preserved_is_confirmed = matching_existing.is_confirmed if matching_existing else False
                preserved_confirmed_by = matching_existing.confirmed_by if matching_existing else ""
                preserved_confirmed_date = matching_existing.confirmed_date if matching_existing else None

                raw_therapist = str(s_item.get("therapist", "")).strip()
                raw_therapist_id = str(s_item.get("therapist_id", "")).strip() or raw_therapist

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

                slot_id_val = s_item.get("attended_slot")
                slot_label_val = s_item.get("slot_label") or slot_label_lookup.get(slot_id_val, "")

                PatientSessionAttendance.objects.create(
                    registration_number=registration_number,
                    attendance_date=date_obj,
                    therapy_id=tid,
                    therapy_name=ct.get("therapy_name"),
                    attended_slot=slot_id_val,
                    slot_label=slot_label_val,
                    therapist=t_name,
                    therapist_id=t_id,
                    is_confirmed=preserved_is_confirmed,
                    confirmed_by=preserved_confirmed_by,
                    confirmed_date=preserved_confirmed_date,
                    sessions_attended=1,
                    session_id=preserved_session_id,
                    created_by=employee_id,
                    created_date=timezone.now(),
                    is_active=True
                )

        # 3. If attendance_doc exists, update monthly PatientAttendance record
        if attendance_doc:
            all_month_sessions = [
                r for r in PatientSessionAttendance.objects.filter(registration_number=registration_number)
                if r.is_active and r.attendance_date and parse_date_only(r.attendance_date) and parse_date_only(r.attendance_date).year == date_obj.year
                and parse_date_only(r.attendance_date).month == date_obj.month
            ]

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
@permission_classes([HasRolePermission])
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

            t_details = safe_json_parse(att.get("therapy_details"))
            extra_details = safe_json_parse(att.get("extra_attending_details"))
            not_details = safe_json_parse(att.get("not_attending_details"))

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

            for x in extra_details:
                if isinstance(x, dict):
                    xname = x.get("therapy_name")
                    tid = x.get("therapy_id") or x.get("therapy_type") or ""
                    xsessions = int(x.get("sessions") or 0)
                    if xname:
                        if xname not in patient_planned_therapies[reg]:
                            patient_planned_therapies[reg][xname] = {"scheduled": 0, "therapy_id": tid}
                        patient_planned_therapies[reg][xname]["scheduled"] += xsessions

            for n in not_details:
                if isinstance(n, dict):
                    nname = n.get("therapy_name")
                    nsessions = int(n.get("sessions") or 0)
                    if nname and nname in patient_planned_therapies[reg]:
                        patient_planned_therapies[reg][nname]["scheduled"] = max(
                            0, patient_planned_therapies[reg][nname]["scheduled"] - nsessions
                        )

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
@permission_classes([HasRolePermission])
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

        # Fetch PatientAttendance records from PyMongo to get allotted/planned sessions per therapy
        db = connection.cursor().db.connection
        collection = db['milestone_backend_patientattendance']
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
                patient_planned_therapies[reg] = {
                    "therapies": {},
                    "child_total_planned": 0
                }

            try:
                monthly_planned_total = int(att.get("session") or 0)
            except:
                monthly_planned_total = 0

            t_details = safe_json_parse(att.get("therapy_details"))
            extra_details = safe_json_parse(att.get("extra_attending_details"))
            not_details = safe_json_parse(att.get("not_attending_details"))

            total_extra = sum(int(x.get("sessions") or 0) for x in extra_details if isinstance(x, dict))
            total_not = sum(int(n.get("sessions") or 0) for n in not_details if isinstance(n, dict))

            monthly_planned_total = max(0, monthly_planned_total - total_not + total_extra)

            t_planned_map = {}
            for t in t_details:
                if isinstance(t, dict):
                    tname = t.get("therapy_name")
                    sched = int(t.get("sesion_per_therapy") or t.get("sessions_per_month") or 0)
                    if tname:
                        t_planned_map[tname] = sched

            for x in extra_details:
                if isinstance(x, dict):
                    xname = x.get("therapy_name")
                    xsessions = int(x.get("sessions") or 0)
                    if xname:
                        t_planned_map[xname] = t_planned_map.get(xname, 0) + xsessions

            for n in not_details:
                if isinstance(n, dict):
                    nname = n.get("therapy_name")
                    nsessions = int(n.get("sessions") or 0)
                    if nname:
                        t_planned_map[nname] = max(0, t_planned_map.get(nname, 0) - nsessions)

            for tname, sched in t_planned_map.items():
                patient_planned_therapies[reg]["therapies"][tname] = sched

            sum_planned = sum(t_planned_map.values())
            patient_planned_therapies[reg]["child_total_planned"] = max(monthly_planned_total, sum_planned)

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
            
            p_info = patient_planned_therapies.get(reg, {})
            planned_count = p_info.get("therapies", {}).get(tname, 0)
            child_allotted_count = p_info.get("child_total_planned", 0)

            key = (reg, tname)
            if key not in matrix_data:
                matrix_data[key] = {
                    "registration_number": reg,
                    "patient_name": patient_names.get(reg, "Unknown Patient"),
                    "therapy_name": tname,
                    "allotted_sessions": planned_count,
                    "child_allotted_sessions": child_allotted_count,
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
@permission_classes([HasRolePermission])
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


def parse_date_only(d):
    if not d:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        try:
            return datetime.strptime(d[:10], '%Y-%m-%d').date()
        except:
            return None
    return None


@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_attendance_vs_registered_report(request):
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

        # 1. Fetch earliest PatientAttendance date for each registration_number
        pa_cursor = collection.find({
            "$or": [
                {"is_active": True},
                {"is_active": {"$exists": False}}
            ]
        }, {"registration_number": 1, "attendance_date": 1})

        first_pa_map = {}
        for doc in pa_cursor:
            reg = str(doc.get("registration_number", "")).strip()
            att_d = parse_date_only(doc.get("attendance_date"))
            if reg and att_d:
                if reg not in first_pa_map or att_d < first_pa_map[reg]:
                    first_pa_map[reg] = att_d

        # 2. Fetch earliest PatientSessionAttendance date for each registration_number
        sa_collection = db['milestone_backend_patientsessionattendance']
        sa_cursor = sa_collection.find({
            "$or": [
                {"is_active": True},
                {"is_active": {"$exists": False}}
            ]
        }, {"registration_number": 1, "attendance_date": 1})

        first_sa_map = {}
        for doc in sa_cursor:
            reg = str(doc.get("registration_number", "")).strip()
            att_d = parse_date_only(doc.get("attendance_date"))
            if reg and att_d:
                if reg not in first_sa_map or att_d < first_sa_map[reg]:
                    first_sa_map[reg] = att_d

        # 3. Fetch all registrations
        all_registrations = list(Registration.objects.all().order_by('-id'))

        today_date = date.today()

        joined_this_month = []
        registered_this_month = []
        without_therapy_list = []
        without_therapy_this_month = []

        total_registered_this_month_count = 0
        total_joined_therapy_this_month_count = 0

        for r in all_registrations:
            reg = str(r.registration_number or "").strip()
            if not reg:
                continue
            
            patient_name = r.name_of_child or "Unknown Patient"
            reg_d = parse_date_only(r.date) or parse_date_only(getattr(r, 'created_date', None))
            phone = r.mother_phone_number or r.father_phone_number or "N/A"
            guardian = r.mother_name or r.father_name or r.guardian_name or "N/A"

            pa_date = first_pa_map.get(reg)
            sa_date = first_sa_map.get(reg)

            therapy_join_date = None
            first_source = None

            if pa_date and sa_date:
                if pa_date <= sa_date:
                    therapy_join_date = pa_date
                    first_source = "Monthly Attendance"
                else:
                    therapy_join_date = sa_date
                    first_source = "Session Attendance"
            elif pa_date:
                therapy_join_date = pa_date
                first_source = "Monthly Attendance"
            elif sa_date:
                therapy_join_date = sa_date
                first_source = "Session Attendance"

            is_reg_this_month = bool(reg_d and reg_d.year == year and reg_d.month == month)
            is_joined_this_month = bool(therapy_join_date and therapy_join_date.year == year and therapy_join_date.month == month)

            if is_reg_this_month:
                total_registered_this_month_count += 1

            if is_joined_this_month:
                total_joined_therapy_this_month_count += 1

            gap_days = (therapy_join_date - reg_d).days if (therapy_join_date and reg_d) else None

            patient_item = {
                "registration_number": reg,
                "patient_name": patient_name,
                "registration_date": reg_d.strftime('%Y-%m-%d') if reg_d else "N/A",
                "therapy_join_date": therapy_join_date.strftime('%Y-%m-%d') if therapy_join_date else "Not Joined Yet",
                "first_attendance_source": first_source or "None",
                "gap_days": gap_days,
                "phone": phone,
                "guardian": guardian,
                "has_therapy": bool(therapy_join_date)
            }

            if is_joined_this_month:
                joined_this_month.append(patient_item)

            if is_reg_this_month:
                registered_this_month.append(patient_item)
                if not therapy_join_date:
                    without_therapy_this_month.append(patient_item)

            if not therapy_join_date:
                days_since_reg = (today_date - reg_d).days if reg_d else 0
                item_without = {**patient_item, "days_since_registration": days_since_reg}
                without_therapy_list.append(item_without)

        # Sort lists
        joined_this_month.sort(key=lambda x: x["therapy_join_date"], reverse=True)
        registered_this_month.sort(key=lambda x: x["registration_date"], reverse=True)
        without_therapy_list.sort(key=lambda x: x["registration_date"], reverse=True)

        avg_days_to_join = 0
        valid_gaps = [x["gap_days"] for x in joined_this_month if x["gap_days"] is not None and x["gap_days"] >= 0]
        if valid_gaps:
            avg_days_to_join = round(sum(valid_gaps) / len(valid_gaps), 1)

        return Response({
            "status": "success",
            "month": month,
            "year": year,
            "summary": {
                "total_registered_this_month": total_registered_this_month_count,
                "total_joined_this_month": total_joined_therapy_this_month_count,
                "without_therapy_this_month": len(without_therapy_this_month),
                "without_therapy_all_time": len(without_therapy_list),
                "avg_days_to_join": avg_days_to_join
            },
            "data": {
                "joined_this_month": joined_this_month,
                "registered_this_month": registered_this_month,
                "without_therapy_this_month": without_therapy_this_month,
                "without_therapy_all_time": without_therapy_list
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        import traceback
        print("Error in get_attendance_vs_registered_report:", traceback.format_exc())
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


