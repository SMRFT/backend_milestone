import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'milestone.settings')
django.setup()

from milestone_backend.models import GoalDomain, TherapyDetails

print("=== ALL DOMAINS IN DB ===")
for d in GoalDomain.objects.all():
    print(f"ID: {d.pk} | Name: {d.name} | Therapy Type in DB: '{d.therapy_type}' | Domain No: {d.domain_no}")
