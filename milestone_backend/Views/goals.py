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
from django.http import FileResponse
import mimetypes
import json
import os
import certifi
from dotenv import load_dotenv

load_dotenv()  # Load from .env if present

# =====================================================
# MONGO CLIENT & GRIDFS HELPERS (SINGLETON PATTERN)
# =====================================================

_mongo_client = None

def get_mongo_client():
    global _mongo_client
    if _mongo_client is None:
        mongo_uri = os.environ.get("GLOBAL_DB_HOST")
        # Initialize MongoClient simply. 
        # Pymongo will handle TLS if specified in the URI.
        _mongo_client = MongoClient(mongo_uri)
    return _mongo_client

def get_gridfs():
    client = get_mongo_client()
    db_name = os.environ.get("MILESTONE_DB_NAME", "Milestone")
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
    """Note: Avoid using this for large files to prevent MemoryError"""
    fs = get_gridfs()
    try:
        file = fs.get(ObjectId(file_id))
        # Use a small chunk size to read if we must read it all at once (still risky for base64)
        return base64.b64encode(file.read()).decode("utf-8")
    except Exception as e:
        print(f"Error reading file for base64 {file_id}: {str(e)}")
        raise


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
        videos = data.pop("goalsvideo", [])

        # Normalize JSON fields
        for field in ["goals", "goalsphoto", "goalsvideo"]:
            value = data.get(field, [])
            if isinstance(value, str):
                try:
                    data[field] = json.loads(value)
                except json.JSONDecodeError:
                    data[field] = []

        image_ids = []
        if isinstance(images, list):
            for img in images:
                if img.startswith("data:"): # Only save if it's new base64 data
                    image_ids.append(
                        save_image_to_gridfs(
                            img,
                            filename=f"goals_photo_{timezone.now().timestamp()}.png"
                        )
                    )
                else: 
                    image_ids.append(img) # Keep existing ID

        data["goalsphoto"] = image_ids

        video_ids = []
        if isinstance(videos, list):
            for vid in videos:
                if vid.startswith("data:"):
                    # For videos, we might need a different extension, 
                    # but save_image_to_gridfs is generic enough if we pass right filename
                    # However, let's detect mime if possible or just use mp4 as default for mobile
                    ext = "mp4"
                    if "video/quicktime" in vid: ext = "mov"
                    elif "video/webm" in vid: ext = "webm"
                    
                    video_ids.append(
                        save_image_to_gridfs(
                            vid,
                            filename=f"goals_video_{timezone.now().timestamp()}.{ext}"
                        )
                    )
                else:
                    video_ids.append(vid)
        
        data["goalsvideo"] = video_ids

        serializer = GoalsAssessmentSerializer(data=data)
        if serializer.is_valid():
            instance = serializer.save(
                created_by=employee_id,
                lastmodified_by=employee_id,
                lastmodified_date=timezone.now()
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

    # Ensure goalsvideo is a list
    goalsvideo_data = data.get("goalsvideo", [])
    if isinstance(goalsvideo_data, str):
        try:
            data["goalsvideo"] = json.loads(goalsvideo_data)
        except json.JSONDecodeError:
            data["goalsvideo"] = []

    # Handle NEW media in PATCH (if any base64 passed)
    if "goalsphoto" in data:
        new_photos = []
        for img in data["goalsphoto"]:
            if isinstance(img, str) and img.startswith("data:"):
                new_photos.append(save_image_to_gridfs(img, filename=f"goals_photo_{timezone.now().timestamp()}.png"))
            else:
                new_photos.append(img)
        data["goalsphoto"] = new_photos

    if "goalsvideo" in data:
        new_videos = []
        for vid in data["goalsvideo"]:
            if isinstance(vid, str) and vid.startswith("data:"):
                ext = "mp4" # default
                if "video/quicktime" in vid: ext = "mov"
                new_videos.append(save_image_to_gridfs(vid, filename=f"goals_video_{timezone.now().timestamp()}.{ext}"))
            else:
                new_videos.append(vid)
        data["goalsvideo"] = new_videos

    # Ensure goals is a list
    goals_data = data.get("goals", [])
    if isinstance(goals_data, str):
        try:
            data["goals"] = json.loads(goals_data)
        except json.JSONDecodeError:
            data["goals"] = []

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

@api_view(["GET"])
def view_goal_file(request, file_id):
    """Serve files directly from GridFS for video playback and high-res images"""
    try:
        fs = get_gridfs()
        file = fs.get(ObjectId(file_id))
        
        filename = getattr(file, 'filename', f"file_{file_id}")
        content_type, _ = mimetypes.guess_type(filename)
        
        if not content_type:
            # Fallback for common types if guess fails
            if filename.endswith('.mp4'): content_type = 'video/mp4'
            elif filename.endswith('.png'): content_type = 'image/png'
            elif filename.endswith('.jpg') or filename.endswith('.jpeg'): content_type = 'image/jpeg'
            else: content_type = 'application/octet-stream'

        # FileResponse handles streaming automatically from file-like objects (GridOut)
        response = FileResponse(file, content_type=content_type)
        # Enable seeking for videos (Range requests)
        response['Accept-Ranges'] = 'bytes'
        return response
    except gridfs.errors.NoFile:
        return Response({"error": "File not found"}, status=404)
    except Exception as e:
        print(f"Error serving file {file_id}: {str(e)}")
        return Response({"error": "Internal server error during file retrieval"}, status=500)
