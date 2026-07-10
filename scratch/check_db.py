import os
import sys
import django

# Add the backend_milestone directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'milestone.settings')
django.setup()

from milestone_backend.models import GoalDomain, GoalLibrary, TherapyDetails, GoalLevel

print("All TherapyDetails:")
for t in TherapyDetails.objects.all():
    print(f"  - {t.therapy_name} ({t.therapy_id})")

print("\nAll GoalDomains:")
for d in GoalDomain.objects.all():
    print(f"  - {d.name} ({d.domain_no}) - therapy: {d.therapy_type}")
