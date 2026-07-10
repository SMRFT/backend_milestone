import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'milestone.settings')
django.setup()

from milestone_backend.models import DevelopmentGoals
from milestone_backend.serializers import DevelopmentGoalsSerializer

print("=== TESTING DEVELOPMENT GOALS SERIALIZATION ===")
qs = DevelopmentGoals.objects.all()
serializer = DevelopmentGoalsSerializer(qs, many=True)
data = serializer.data
print(f"Total serialized items: {len(data)}")
if len(data) > 0:
    print("\nSample Item Metadata:")
    item = data[0]
    print(f"ID: {item.get('id')}")
    print(f"Reg: {item.get('registration_number')}")
    print(f"Date: {item.get('date')}")
    print(f"DOB: {item.get('dob')} | Father: {item.get('father')}")
    print(f"Created By Name: {item.get('created_by_name')} | Designation: {item.get('created_by_designation')}")
    print(f"Goals Count: {len(item.get('development_goals', []))}")
    print("\nFirst Goal details:")
    if item.get('development_goals'):
        print(item.get('development_goals')[0])
