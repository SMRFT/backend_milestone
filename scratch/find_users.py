import os
import sys
import django

# Add the backend_milestone directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'milestone.settings')
django.setup()

from milestone_backend.models import EmployeeRegistration

for emp in EmployeeRegistration.objects.all():
    print(f"Name: {emp.name}, Email: {emp.email}, Role: {emp.role}, EmpID: {emp.empid}")
