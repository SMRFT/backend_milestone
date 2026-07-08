from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime
from milestone_backend.models import DevelopmentGoals
from milestone_backend.serializers import DevelopmentGoalsSerializer
from pyauth.auth import HasRolePermission
import calendar

def validate_and_update_goals(existing_goals, incoming_goals, current_employee_id):
    """
    Checks if the user has edited or deleted any goals created by other employees.
    Also ensures any new goals get the current_employee_id set.
    """
    if not current_employee_id:
        return False, "User not authenticated / employee ID missing."

    current_employee_id = str(current_employee_id)
    
    # Ensure existing_goals is a list of dicts
    if isinstance(existing_goals, str):
        import json
        try:
            existing_goals = json.loads(existing_goals)
        except:
            existing_goals = []
    if not isinstance(existing_goals, list):
        existing_goals = []

    # Ensure incoming_goals is a list of dicts
    if isinstance(incoming_goals, str):
        import json
        try:
            incoming_goals = json.loads(incoming_goals)
        except:
            incoming_goals = []
    if not isinstance(incoming_goals, list):
        incoming_goals = []

    # Fetch and cache therapy mapping
    from milestone_backend.models import TherapyDetails, GoalDomain, GoalLevel
    
    therapy_map = {}
    for t in TherapyDetails.objects.all():
        tid = str(t.therapy_id or '').strip()
        tname = str(t.therapy_name or '').strip()
        t_id_str = str(t.pk or '').strip()
        if tid:
            therapy_map[tid.lower()] = tid
        if tname:
            therapy_map[tname.lower()] = tid
        if t_id_str:
            therapy_map[t_id_str.lower()] = tid

    # Cache domain mapping
    domain_map = {}
    for d in GoalDomain.objects.all():
        dno = str(d.domain_no or '').strip()
        dname = str(d.name or '').strip()
        d_id_str = str(d.pk or '').strip()
        if dno:
            domain_map[dno.lower()] = dno
        if dname:
            domain_map[dname.lower()] = dno
        if d_id_str:
            domain_map[d_id_str.lower()] = dno

    # Cache level mapping
    level_map = {}
    for l in GoalLevel.objects.all():
        lid = str(l.level_id or '').strip()
        lname = str(l.name or '').strip()
        l_id_str = str(l.pk or '').strip()
        if lid:
            level_map[lid.lower()] = lid
        if lname:
            level_map[lname.lower()] = lid
        if l_id_str:
            level_map[l_id_str.lower()] = lid

    def get_norm_therapy(val):
        s = str(val or '').strip().lower()
        return therapy_map.get(s, val)

    def get_norm_domain(val):
        s = str(val or '').strip().lower()
        return domain_map.get(s, val)

    def get_norm_level(val):
        s = str(val or '').strip().lower()
        return level_map.get(s, val)

    # Build lookup map for existing goals: key is (therapy, domain, goal)
    existing_map = {}
    for g in existing_goals:
        if not isinstance(g, dict):
            continue
        # Normalize fields
        norm_t = get_norm_therapy(g.get('therapy', ''))
        norm_d = get_norm_domain(g.get('domain', ''))
        g['therapy'] = norm_t
        g['domain'] = norm_d
        g['level'] = get_norm_level(g.get('level', ''))

        key = (
            str(norm_t).strip().lower(), 
            str(norm_d).strip().lower(), 
            str(g.get('goal', '')).strip().lower()
        )
        existing_map[key] = g

    # Build lookup map for incoming goals
    incoming_map = {}
    for g in incoming_goals:
        if not isinstance(g, dict):
            continue
        # Normalize fields
        norm_t = get_norm_therapy(g.get('therapy', ''))
        norm_d = get_norm_domain(g.get('domain', ''))
        g['therapy'] = norm_t
        g['domain'] = norm_d
        g['level'] = get_norm_level(g.get('level', ''))

        key = (
            str(norm_t).strip().lower(), 
            str(norm_d).strip().lower(), 
            str(g.get('goal', '')).strip().lower()
        )
        incoming_map[key] = g

    # Check for deleted goals
    for key, ext_g in existing_map.items():
        creator_id = ext_g.get('employee_id')
        if creator_id and str(creator_id) != current_employee_id:
            # This goal was created by another employee. Is it missing in incoming?
            if key not in incoming_map:
                return False, f"You are not allowed to delete the goal '{ext_g.get('goal')}' created by employee {creator_id}."

    # Check for edited goals & assign employee_id to new/unassigned goals
    modified_incoming = []
    for g in incoming_goals:
        if not isinstance(g, dict):
            continue
        key = (
            str(g.get('therapy', '')).strip().lower(), 
            str(g.get('domain', '')).strip().lower(), 
            str(g.get('goal', '')).strip().lower()
        )
        
        ext_g = existing_map.get(key)
        if ext_g:
            creator_id = ext_g.get('employee_id')
            if creator_id and str(creator_id) != current_employee_id:
                # Normalize history arrays for comparison
                def norm_hist(h):
                    if not isinstance(h, list): return []
                    return sorted([{str(k): str(v) for k, v in item.items()} for item in h if isinstance(item, dict)], key=lambda x: x.get('date', ''))
                
                ext_hist = norm_hist(ext_g.get('history'))
                inc_hist = norm_hist(g.get('history'))
                
                # Check if percentage, status, or history changed
                if (str(g.get('percentage')) != str(ext_g.get('percentage')) or 
                    str(g.get('status')) != str(ext_g.get('status')) or 
                    ext_hist != inc_hist):
                    return False, f"You are not allowed to edit the goal '{ext_g.get('goal')}' created by employee {creator_id}."
                
                # Retain original employee_id
                g['employee_id'] = ext_g.get('employee_id')
            else:
                # If it had no employee_id or belonged to the current user, ensure it has one now
                g['employee_id'] = current_employee_id
        else:
            # New goal added, set current employee_id
            g['employee_id'] = current_employee_id
            
        modified_incoming.append(g)

    return True, modified_incoming

@api_view(["POST", "GET"])
@permission_classes([HasRolePermission])
def development_goals_list_create(request):
    employee_id = request.data.get('auth-user-id')

    if request.method == "POST":
        # Safe copy of payload data
        if hasattr(request.data, 'copy'):
            data = request.data.copy()
        else:
            data = dict(request.data)

        reg_number = data.get('registration_number')
        date_str = data.get('date')

        if not reg_number or not date_str:
            return Response({"error": "registration_number and date are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if a record exists for this patient in the same month and year
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
            success, result = validate_and_update_goals(
                existing_record.development_goals,
                data.get('development_goals', []),
                employee_id
            )
            if not success:
                return Response({"error": result}, status=status.HTTP_403_FORBIDDEN)
            
            data['development_goals'] = result

            serializer = DevelopmentGoalsSerializer(existing_record, data=data, partial=True)
            if serializer.is_valid():
                serializer.save(
                    lastmodified_by=employee_id,
                    lastmodified_date=timezone.now()
                )
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Create New Record
        success, result = validate_and_update_goals(
            [],
            data.get('development_goals', []),
            employee_id
        )
        if not success:
            return Response({"error": result}, status=status.HTTP_403_FORBIDDEN)
        
        data['development_goals'] = result

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
    month_param = request.query_params.get('month')  # e.g., "2026-06", "06", or "6"
    year_param = request.query_params.get('year')    # e.g., "2026"

    qs = DevelopmentGoals.objects.all()
    if reg_number:
        qs = qs.filter(registration_number=reg_number)

    if month_param:
        try:
            if '-' in month_param:
                parts = month_param.split('-')
                if len(parts) >= 2:
                    y = int(parts[0])
                    m = int(parts[1])
                else:
                    y = timezone.now().year
                    m = int(parts[0])
            else:
                m = int(month_param)
                y = int(year_param) if year_param else timezone.now().year

            if 1 <= m <= 12:
                # Calculate first and last days of the month
                first_day = datetime(y, m, 1).date()
                last_day = datetime(y, m, calendar.monthrange(y, m)[1]).date()
                qs = qs.filter(date__range=(first_day, last_day))
        except Exception as e:
            print("Month filter parse error:", e)

    qs = qs.order_by('-date')
    serializer = DevelopmentGoalsSerializer(qs, many=True)
    return Response(serializer.data)

@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([HasRolePermission])
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
        success, result = validate_and_update_goals(
            instance.development_goals,
            request.data.get('development_goals', []),
            employee_id
        )
        if not success:
            return Response({"error": result}, status=status.HTTP_403_FORBIDDEN)

        if hasattr(request.data, 'copy'):
            req_data = request.data.copy()
        else:
            req_data = dict(request.data)
            
        req_data['development_goals'] = result

        serializer = DevelopmentGoalsSerializer(instance, data=req_data, partial=(request.method == "PATCH"))
        if serializer.is_valid():
            serializer.save(
                lastmodified_by=employee_id,
                lastmodified_date=timezone.now()
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        # Delete only allowed if caller is the record creator and no other employee's goals are inside
        is_creator = not instance.created_by or str(instance.created_by) == str(employee_id)
        
        has_other_employee_goals = False
        goals = instance.development_goals or []
        if isinstance(goals, str):
            import json
            try:
                goals = json.loads(goals)
            except:
                goals = []
        
        for g in goals:
            if isinstance(g, dict) and g.get('employee_id') and str(g.get('employee_id')) != str(employee_id):
                has_other_employee_goals = True
                break

        if not is_creator or has_other_employee_goals:
            return Response(
                {"error": "You are not allowed to delete this record because it contains goals created by other employees or was created by another employee."},
                status=status.HTTP_403_FORBIDDEN
            )

        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
