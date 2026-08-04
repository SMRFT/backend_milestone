import json
import traceback
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from pyauth.auth import HasRolePermission

from .dbcollection import milestone_db
from ..models import Registration

col = milestone_db['milestone_backend_qnaform']


def safe_json_parse(data):
    if isinstance(data, str):
        try:
            return json.loads(data)
        except:
            return []
    elif isinstance(data, list):
        return data
    return []


def make_naive(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None)
    if isinstance(val, date):
        return datetime.combine(val, datetime.min.time())
    if isinstance(val, str):
        try:
            return datetime.strptime(val[:19].replace('T', ' '), '%Y-%m-%d %H:%M:%S').replace(tzinfo=None)
        except:
            try:
                return datetime.strptime(val[:10], '%Y-%m-%d').replace(tzinfo=None)
            except:
                return None
    return None


@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_qna_list(request):
    """
    Get Q&A records. By default, returns records from the LAST 1 WEEK (7 days).
    Query parameters:
      - filter: "last_week" (default), "all", "unanswered", "answered"
      - start_date: YYYY-MM-DD (optional)
      - end_date: YYYY-MM-DD (optional)
      - search: keyword search in qa_id, question, category, asked_by, patient_name, registration_number
    """
    try:
        filter_type = request.GET.get('filter', 'last_week').lower().strip()
        search_query = request.GET.get('search', '').lower().strip()
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        # Fetch active Q&A records using native PyMongo
        docs = list(col.find({
            "$or": [
                {"is_active": True},
                {"is_active": {"$exists": False}}
            ]
        }))

        now = datetime.now()
        one_week_ago = now - timedelta(days=7)

        # Parse date boundaries if provided
        start_dt = None
        end_dt = None
        if start_date_str:
            try:
                start_dt = datetime.strptime(start_date_str[:10], '%Y-%m-%d')
            except:
                pass
        if end_date_str:
            try:
                end_dt = datetime.strptime(end_date_str[:10], '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            except:
                pass

        result = []
        for d in docs:
            qa_id = d.get('qa_id', '')
            question = d.get('question', '')
            category = d.get('category', 'General')
            asked_by = d.get('asked_by', '')
            reg_no = d.get('registration_number', '')
            patient_name = d.get('patient_name', '')
            status_val = d.get('status', 'Unanswered')
            answers_raw = d.get('answers', [])
            answers = safe_json_parse(answers_raw)

            # Extract created date
            created_dt = make_naive(d.get('created_date')) or now

            # Filter by last week (default) unless "all" or specific dates requested
            if filter_type == 'last_week' and not start_dt and not end_dt:
                if created_dt < one_week_ago:
                    continue

            # Custom Date Filter
            if start_dt and created_dt < start_dt:
                continue
            if end_dt and created_dt > end_dt:
                continue

            # Status Filter
            if filter_type == 'unanswered' and status_val.lower() == 'answered':
                continue
            if filter_type == 'answered' and status_val.lower() != 'answered':
                continue

            # Search Filter
            if search_query:
                q_text = f"{qa_id} {question} {category} {asked_by} {reg_no} {patient_name}".lower()
                if search_query not in q_text:
                    continue

            result.append({
                "_id": str(d.get('_id')),
                "qa_id": qa_id,
                "question": question,
                "category": category,
                "asked_by": asked_by,
                "registration_number": reg_no,
                "patient_name": patient_name,
                "answers": answers,
                "status": status_val,
                "created_date": created_dt.strftime('%Y-%m-%d %H:%M:%S'),
                "created_by": d.get('created_by', ''),
                "answer_count": len(answers)
            })

        # Sort newest first
        result.sort(key=lambda x: x['created_date'], reverse=True)

        return Response({
            "status": "success",
            "count": len(result),
            "filter_applied": filter_type,
            "data": result
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print("Error in get_qna_list:", traceback.format_exc())
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasRolePermission])
def create_question(request):
    """
    Create a new question using native PyMongo. Automatically assigns sequence number Q026/0000001.
    """
    try:
        data = request.data
        question = str(data.get('question', '')).strip()

        if not question:
            return Response({"error": "Question text is required"}, status=status.HTTP_400_BAD_REQUEST)

        category = str(data.get('category', 'General')).strip() or 'General'
        asked_by = str(data.get('asked_by', '')).strip()
        reg_no = str(data.get('registration_number', '')).strip()
        patient_name = str(data.get('patient_name', '')).strip()
        employee_id = data.get('auth-user-id') or localStorage_user(request)

        # Lookup patient_name if reg_no supplied but patient_name missing
        if reg_no and not patient_name:
            patient_obj = Registration.objects.filter(registration_number=reg_no).first()
            if patient_obj:
                patient_name = patient_obj.name_of_child or ''

        # Generate sequence ID Q026/0000001 using native PyMongo
        now = datetime.now()
        current_year = now.year
        year_part = f"{current_year % 1000:03d}"
        prefix = f"Q{year_part}/"

        last_doc = col.find_one({"qa_id": {"$regex": f"^{prefix}"}}, sort=[("qa_id", -1)])
        if last_doc and last_doc.get("qa_id"):
            try:
                parts = last_doc["qa_id"].split("/")
                seq = int(parts[1]) + 1 if len(parts) == 2 else 1
            except:
                seq = 1
        else:
            seq = 1

        new_qa_id = f"{prefix}{seq:07d}"

        # Initial answer if provided during creation
        initial_answer = str(data.get('initial_answer', '')).strip()
        answers_list = []
        status_val = 'Unanswered'

        if initial_answer:
            answers_list.append({
                "answer_id": "ANS-001",
                "answer": initial_answer,
                "answered_by": asked_by or employee_id or "Staff",
                "answered_date": now.strftime('%Y-%m-%d %H:%M:%S')
            })
            status_val = 'Answered'

        created_date_str = now.strftime('%Y-%m-%d %H:%M:%S')

        doc = {
            "qa_id": new_qa_id,
            "question": question,
            "category": category,
            "asked_by": asked_by or "Anonymous",
            "registration_number": reg_no,
            "patient_name": patient_name,
            "answers": answers_list,
            "status": status_val,
            "created_by": employee_id or "System",
            "created_date": created_date_str,
            "is_active": True
        }

        col.insert_one(doc)

        return Response({
            "status": "success",
            "message": "Question created successfully",
            "data": {
                "qa_id": new_qa_id,
                "question": question,
                "category": category,
                "asked_by": doc["asked_by"],
                "registration_number": reg_no,
                "patient_name": patient_name,
                "answers": answers_list,
                "status": status_val,
                "created_date": created_date_str
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        print("Error in create_question:", traceback.format_exc())
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasRolePermission])
def add_answer(request):
    """
    Add/Append an answer to an existing question using native PyMongo collection operations.
    """
    try:
        data = request.data
        qa_id = str(data.get('qa_id', '')).strip()
        answer_text = str(data.get('answer', '')).strip()
        answered_by = str(data.get('answered_by', '')).strip()
        employee_id = data.get('auth-user-id') or 'System'

        if not qa_id or not answer_text:
            return Response({"error": "qa_id and answer text are required"}, status=status.HTTP_400_BAD_REQUEST)

        doc = col.find_one({"qa_id": qa_id, "$or": [{"is_active": True}, {"is_active": {"$exists": False}}]})
        if not doc:
            return Response({"error": f"Question with ID '{qa_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

        curr_answers = safe_json_parse(doc.get("answers", []))
        ans_num = len(curr_answers) + 1
        new_ans_id = f"ANS-{ans_num:03d}"

        new_answer = {
            "answer_id": new_ans_id,
            "answer": answer_text,
            "answered_by": answered_by or employee_id or "Staff",
            "answered_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        curr_answers.append(new_answer)

        col.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "answers": curr_answers,
                "status": "Answered",
                "lastmodified_by": employee_id,
                "lastmodified_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }}
        )

        return Response({
            "status": "success",
            "message": "Answer added successfully",
            "data": {
                "qa_id": qa_id,
                "status": "Answered",
                "answers": curr_answers
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print("Error in add_answer:", traceback.format_exc())
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@permission_classes([HasRolePermission])
def update_question(request, qa_id):
    """
    Update question text, category, or status using native PyMongo.
    """
    try:
        doc = col.find_one({"qa_id": qa_id})
        if not doc:
            return Response({"error": f"Question '{qa_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        update_fields = {
            "lastmodified_by": data.get('auth-user-id', 'System'),
            "lastmodified_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        if 'question' in data:
            update_fields['question'] = str(data['question']).strip()
        if 'category' in data:
            update_fields['category'] = str(data['category']).strip()
        if 'status' in data:
            update_fields['status'] = str(data['status']).strip()

        col.update_one({"_id": doc["_id"]}, {"$set": update_fields})

        return Response({
            "status": "success",
            "message": "Question updated successfully"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([HasRolePermission])
def delete_question(request, qa_id):
    """
    Soft-delete a question using native PyMongo.
    """
    try:
        col.update_one(
            {"qa_id": qa_id},
            {"$set": {
                "is_active": False,
                "lastmodified_by": request.data.get('auth-user-id', 'System'),
                "lastmodified_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }}
        )

        return Response({
            "status": "success",
            "message": f"Question '{qa_id}' deleted successfully."
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def localStorage_user(request):
    return request.data.get("auth-user-id") or "Admin"
