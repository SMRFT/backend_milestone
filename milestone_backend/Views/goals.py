from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils import timezone
from datetime import datetime ,timedelta ,date
from django.utils.dateparse import parse_date
from pymongo import MongoClient
import gridfs
import base64
from bson import ObjectId
from pyauth.auth import HasRolePermission
from milestone_backend.models import GoalsAssessment
from milestone_backend.serializers import GoalsAssessmentSerializer, RegistrationSerializer
import os
import certifi
from dotenv import load_dotenv

load_dotenv()  # Load from .env if present

env_type = os.environ.get("ENV_CLASSIFICATION", "local")

mongo_uri = os.environ.get("GLOBAL_DB_HOST")
db_name = os.environ.get("MILESTONE_DB_NAME", "Milestone")

if env_type in ["test", "prod"]:
    client = MongoClient(mongo_uri)
else:
    client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
# =====================================================
# GRIDFS HELPERS (MODEL SAFE)
# =====================================================

def get_gridfs():
    mongo_uri = os.environ.get("GLOBAL_DB_HOST")
    db_name = os.environ.get("MILESTONE_DB_NAME", "Milestone")
    
    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client[db_name]
    return gridfs.GridFS(db)


def save_image_to_gridfs(base64_data, filename):
    fs = get_gridfs()

    if "base64," in base64_data:
        base64_data = base64_data.split("base64,")[1]

    image_data = base64.b64decode(base64_data)
    file_id = fs.put(image_data, filename=filename)

    print("✅ Saved Image:", file_id)
    return str(file_id)


def delete_image_from_gridfs(file_id):
    fs = get_gridfs()
    fs.delete(ObjectId(file_id))
    print("🗑️ Deleted Image:", file_id)


def get_image_base64(file_id):
    fs = get_gridfs()
    file = fs.get(ObjectId(file_id))
    return base64.b64encode(file.read()).decode("utf-8")


# =====================================================
# CREATE + LIST
# =====================================================

@api_view(["POST", "GET"])
@permission_classes([HasRolePermission])
def goals_assessment_list_create(request):
    employee_id = request.data.get('auth-user-id')

    # ---------------- CREATE ----------------
    if request.method == "POST":
        data = request.data.copy()
        images = data.pop("goalsphoto", [])

        # Normalize JSON fields
        for field in ["goals", "goalsphoto"]:
            value = data.get(field, [])
            if isinstance(value, str):
                try:
                    data[field] = json.loads(value)
                except json.JSONDecodeError:
                    data[field] = []

        image_ids = []

        if isinstance(images, list):
            for img in images:
                image_ids.append(
                    save_image_to_gridfs(
                        img,
                        filename=f"goals_{timezone.now().timestamp()}.png"
                    )
                )

        data["goalsphoto"] = image_ids

        serializer = GoalsAssessmentSerializer(data=data)
        if serializer.is_valid():
            instance = serializer.save(
                created_by=employee_id,
                lastmodified_by=employee_id,
                lastmodified_date=datetime.now()
            )
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

    # ---------------- LIST ----------------
    qs = GoalsAssessment.objects.all()
    serializer = GoalsAssessmentSerializer(qs, many=True)
    return Response(serializer.data)


from bson import ObjectId

@api_view(["PATCH"])
@permission_classes([HasRolePermission])
def goals_assessment_update(request, pk):

    try:
        instance = GoalsAssessment.objects.get(_id=ObjectId(pk))
    except:
        return Response({"error": "Assessment not found"}, status=404)

    data = request.data.copy()   # ✅ IMPORTANT
    import json

    # Ensure goalsphoto is a list
    goalsphoto_data = data.get("goalsphoto", [])
    if isinstance(goalsphoto_data, str):
        try:
            data["goalsphoto"] = json.loads(goalsphoto_data)
        except json.JSONDecodeError:
            data["goalsphoto"] = []  # fallback to empty list

    # Ensure goals is a list
    goals_data = data.get("goals", [])
    if isinstance(goals_data, str):
        try:
            data["goals"] = json.loads(goals_data)
        except json.JSONDecodeError:
            data["goals"] = []


    print("PATCH DATA:", data)
    print("GOALS TYPE:", type(data.get("goals")))

    serializer = GoalsAssessmentSerializer(
        instance,
        data=data,
        partial=True
    )

    if serializer.is_valid():
        serializer.save(
            lastmodified_by=data.get('auth-user-id'),
            lastmodified_date=datetime.now()
        )
        return Response(serializer.data)

    return Response(serializer.errors, status=400)


@api_view(["DELETE"])
def delete_goal_image(request, pk, image_id):

    try:
        instance = GoalsAssessment.objects.get(pk=pk)
    except GoalsAssessment.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    if image_id not in instance.goalsphoto:
        return Response({"error": "Image not linked"}, status=400)

    delete_image_from_gridfs(image_id)

    instance.goalsphoto.remove(image_id)
    instance.save(update_fields=["goalsphoto"])

    return Response({"message": "Image deleted"})

@api_view(["GET"])
def view_goal_image(request, image_id):

    try:
        image_base64 = get_image_base64(image_id)
        return Response({
            "image_id": image_id,
            "base64": image_base64
        })
    except Exception:
        return Response({"error": "Image not found"}, status=404)
