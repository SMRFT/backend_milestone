import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'milestone.settings')
django.setup()

from milestone_backend.models import ActivityLibrary

print("=== SAMPLE ACTIVITY LIBRARY ENTRIES IN DB ===")
distinct_therapies = set()
distinct_domains = set()

for a in ActivityLibrary.objects.all():
    distinct_therapies.add(a.therapy_type)
    distinct_domains.add(a.domain)

print("Distinct therapy_type values in ActivityLibrary:")
for t in sorted(list(distinct_therapies)):
    print(f"  - '{t}'")

print("\nDistinct domain values in ActivityLibrary:")
for d in sorted(list(distinct_domains)):
    print(f"  - '{d}'")
