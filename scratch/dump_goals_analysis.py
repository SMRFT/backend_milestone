import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'milestone.settings')
django.setup()

from milestone_backend.models import GoalLibrary

print("=== SAMPLE GOAL LIBRARY ENTRIES IN DB ===")
distinct_therapies = set()
distinct_domains = set()
distinct_levels = set()

for g in GoalLibrary.objects.all():
    distinct_therapies.add(g.therapy_type)
    distinct_domains.add(g.domain)
    distinct_levels.add(g.level)

print("Distinct therapy_type values in GoalLibrary:")
for t in sorted(list(distinct_therapies)):
    print(f"  - '{t}'")

print("\nDistinct domain values in GoalLibrary (first 20):")
for d in sorted(list(distinct_domains))[:20]:
    print(f"  - '{d}'")

print("\nDistinct level values in GoalLibrary:")
for l in sorted(list(distinct_levels)):
    print(f"  - '{l}'")
