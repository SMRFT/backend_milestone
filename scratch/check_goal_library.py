import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'milestone.settings')
django.setup()

from milestone_backend.models import GoalLibrary

print("=== CHECKING GOAL LIBRARY ===")
unnormalized_therapy = 0
unnormalized_domain = 0
unnormalized_level = 0

for g in GoalLibrary.objects.all():
    # check therapy_type
    if g.therapy_type and not g.therapy_type.startswith("THP"):
        unnormalized_therapy += 1
        print(f"Goal: '{g.goal_name[:40]}' | Unnormalized therapy_type: '{g.therapy_type}'")
    
    # check domain
    # Domain should be a domain_no like OT001, AT001, etc. (usually 2 uppercase letters + 3 digits)
    if g.domain:
        is_normalized = len(g.domain) == 5 and g.domain[:2].isalpha() and g.domain[2:].isdigit()
        if not is_normalized:
            unnormalized_domain += 1
            print(f"Goal: '{g.goal_name[:40]}' | Unnormalized domain: '{g.domain}'")
            
    # check level
    # Level should be level_id like LVL01
    if g.level:
        is_normalized = g.level.startswith("LVL")
        if not is_normalized:
            unnormalized_level += 1
            print(f"Goal: '{g.goal_name[:40]}' | Unnormalized level: '{g.level}'")

print(f"\nSummary:")
print(f"Unnormalized therapy_type count: {unnormalized_therapy}")
print(f"Unnormalized domain count: {unnormalized_domain}")
print(f"Unnormalized level count: {unnormalized_level}")
