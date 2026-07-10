import os
import sys
import django
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'milestone.settings')
django.setup()

from milestone_backend.models import DevelopmentGoals

records = list(DevelopmentGoals.objects.all())
if records:
    r = records[0]
    print(f"ID: {r.pk}")
    print(f"Reg: {r.registration_number}")
    print(f"Date: {r.date}")
    print("development_goals:")
    print(json.dumps(r.development_goals, indent=2))
