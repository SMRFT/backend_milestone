import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'milestone.settings')
django.setup()

from milestone_backend.models import DevelopmentGoals

print("=== DEVELOPMENT GOALS RECORDS ===")
records = list(DevelopmentGoals.objects.all())
print(f"Total records: {len(records)}")
for r in records[:5]:
    print(f"ID: {r.pk} | Reg: {r.registration_number} | Date: {r.date} | Goals Count: {len(r.development_goals)}")
