import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'milestone.settings')
django.setup()

from milestone_backend.models import TherapyDetails

print("=== ALL THERAPY DETAILS ===")
for t in TherapyDetails.objects.all():
    print(f"ID: {t.pk} | Name: '{t.therapy_name}' | Therapy ID: '{t.therapy_id}'")
