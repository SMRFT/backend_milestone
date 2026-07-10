import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'milestone.settings')
django.setup()

from milestone_backend.models import GoalDomain

print("=== NORMALIZING DOMAINS ===")
for d in GoalDomain.objects.all():
    old_therapy = d.therapy_type
    d.save()
    print(f"Domain: {d.name} | old therapy_type: '{old_therapy}' -> new: '{d.therapy_type}' | domain_no: {d.domain_no}")
