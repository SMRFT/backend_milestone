from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime
from ..models import Notification, Registration
from django.views.decorators.csrf import csrf_exempt
from pyauth.auth import HasRolePermission

@api_view(['POST'])
@permission_classes([HasRolePermission])
def create_notification(request):
    """
    API endpoint to initialize and assign notification to selected members.
    Auto-generates notification_id like NOTI/26/00001 upon save.
    """
    try:
        data = request.data
        title = data.get('title', '').strip()
        sub = data.get('sub', '').strip()
        raw_members = data.get('members', [])
        created_by = data.get('auth-user-id', 'Admin')

        if not title or not sub:
            return Response({
                "status": "error",
                "message": "Title and Subject (sub) are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not raw_members:
            return Response({
                "status": "error",
                "message": "At least one member registration number must be assigned."
            }, status=status.HTTP_400_BAD_REQUEST)

        now_str = datetime.now().isoformat()
        processed_members = []

        for m in raw_members:
            if isinstance(m, dict):
                reg_no = m.get('reg_no')
                name = m.get('name', '')
            else:
                reg_no = str(m)
                name = ''

            if not reg_no:
                continue

            if not name:
                patient = Registration.objects.filter(registration_number=reg_no).first()
                if patient:
                    name = patient.name_of_child or ''

            processed_members.append({
                "reg_no": reg_no,
                "name": name,
                "is_send": False,
                "is_read": False,
                "sent_datetime": None,
                "read_datetime": None
            })

        notification = Notification(
            title=title,
            sub=sub,
            members=processed_members,
            created_by=created_by
        )
        notification.save()

        return Response({
            "status": "success",
            "message": "Notification initialized successfully.",
            "notification_id": notification.notification_id,
            "data": {
                "id": str(notification.id),
                "notification_id": notification.notification_id,
                "title": notification.title,
                "sub": notification.sub,
                "members": notification.members,
                "created_date": notification.created_date
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasRolePermission])
def mark_notification_sent(request):
    """
    Mark notification as sent/delivered for members (updates is_send=True and sent_datetime).
    """
    try:
        notification_id = request.data.get('notification_id')
        reg_no = request.data.get('reg_no')

        if not notification_id:
            return Response({
                "status": "error",
                "message": "notification_id is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        notification = Notification.objects.filter(notification_id=notification_id).first()
        if not notification:
            return Response({
                "status": "error",
                "message": f"Notification '{notification_id}' not found."
            }, status=status.HTTP_404_NOT_FOUND)

        now_str = datetime.now().isoformat()
        members = notification.members or []
        updated = False

        for m in members:
            if not reg_no or m.get('reg_no') == reg_no:
                m['is_send'] = True
                if not m.get('sent_datetime'):
                    m['sent_datetime'] = now_str
                updated = True

        if updated:
            notification.members = members
            notification.save()
            return Response({
                "status": "success",
                "message": f"Notification '{notification_id}' marked as sent.",
                "notification_id": notification.notification_id,
                "members": notification.members
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "error",
                "message": "No matching member found to update."
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_notifications(request):
    """
    Fetch all initialized notifications with delivery and open/read summary stats.
    """
    try:
        notifications = Notification.objects.all().order_by('-created_date')
        result = []
        for n in notifications:
            members = n.members or []
            total_members = len(members)
            sent_count = sum(1 for m in members if m.get('is_send'))
            read_count = sum(1 for m in members if m.get('is_read'))

            result.append({
                "id": str(n.id),
                "notification_id": n.notification_id,
                "title": n.title,
                "sub": n.sub,
                "members": members,
                "total_members": total_members,
                "sent_count": sent_count,
                "read_count": read_count,
                "unread_count": total_members - read_count,
                "created_by": n.created_by,
                "created_date": n.created_date
            })

        return Response({
            "status": "success",
            "count": len(result),
            "data": result
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasRolePermission])
def mark_notification_read(request):
    """
    Mark notification as read for a specific member registration number.
    Updates is_read=True and read_datetime for that member.
    """
    try:
        notification_id = request.data.get('notification_id')
        reg_no = request.data.get('reg_no')

        if not notification_id or not reg_no:
            return Response({
                "status": "error",
                "message": "Both notification_id and reg_no are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        notification = Notification.objects.filter(notification_id=notification_id).first()
        if not notification:
            return Response({
                "status": "error",
                "message": f"Notification '{notification_id}' not found."
            }, status=status.HTTP_404_NOT_FOUND)

        now_str = datetime.now().isoformat()
        updated = False
        members = notification.members or []

        for m in members:
            if m.get('reg_no') == reg_no:
                m['is_read'] = True
                m['read_datetime'] = now_str
                updated = True

        if updated:
            notification.members = members
            notification.save()
            return Response({
                "status": "success",
                "message": f"Notification '{notification_id}' marked as read for member '{reg_no}'.",
                "notification_id": notification.notification_id,
                "members": notification.members
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "error",
                "message": f"Member '{reg_no}' not assigned to notification '{notification_id}'."
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_notification_report(request):
    """
    Returns overall metrics (total sent, total delivered, total opened, open rate %)
    plus detailed breakdown per notification.
    Supports optional start_date and end_date query parameters.
    """
    try:
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        notifications = Notification.objects.all().order_by('-created_date')

        if start_date:
            try:
                start_dt = datetime.strptime(f"{start_date} 00:00:00", "%Y-%m-%d %H:%M:%S")
                if timezone.is_aware(timezone.now()):
                    start_dt = timezone.make_aware(start_dt)
                notifications = notifications.filter(created_date__gte=start_dt)
            except Exception as ex:
                print("Start date filter warning:", ex)

        if end_date:
            try:
                end_dt = datetime.strptime(f"{end_date} 23:59:59", "%Y-%m-%d %H:%M:%S")
                if timezone.is_aware(timezone.now()):
                    end_dt = timezone.make_aware(end_dt)
                notifications = notifications.filter(created_date__lte=end_dt)
            except Exception as ex:
                print("End date filter warning:", ex)

        total_notifications = len(notifications)
        total_delivered = 0
        total_opened = 0

        notification_reports = []

        for n in notifications:
            members = n.members or []
            total_m = len(members)
            sent_m = sum(1 for m in members if m.get('is_send'))
            read_m = sum(1 for m in members if m.get('is_read'))
            unread_m = total_m - read_m

            total_delivered += sent_m
            total_opened += read_m

            open_rate = round((read_m / sent_m * 100), 2) if sent_m > 0 else 0.0

            notification_reports.append({
                "id": str(n.id),
                "notification_id": n.notification_id,
                "title": n.title,
                "sub": n.sub,
                "total_members": total_m,
                "sent_count": sent_m,
                "read_count": read_m,
                "unread_count": unread_m,
                "open_rate_pct": open_rate,
                "created_date": n.created_date,
                "members": members
            })

        overall_open_rate = round((total_opened / total_delivered * 100), 2) if total_delivered > 0 else 0.0

        return Response({
            "status": "success",
            "summary": {
                "total_notifications": total_notifications,
                "total_delivered": total_delivered,
                "total_opened": total_opened,
                "total_unread": total_delivered - total_opened,
                "overall_open_rate_pct": overall_open_rate
            },
            "data": notification_reports
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([HasRolePermission])
def delete_notification(request, pk):
    """
    Delete notification by primary key or notification_id.
    """
    try:
        notification = Notification.objects.filter(notification_id=pk).first()
        if not notification:
            notification = Notification.objects.filter(id=pk).first()

        if not notification:
            return Response({
                "status": "error",
                "message": "Notification not found"
            }, status=status.HTTP_404_NOT_FOUND)

        notification.delete()
        return Response({
            "status": "success",
            "message": "Notification deleted successfully"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
