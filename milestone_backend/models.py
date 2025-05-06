from django.db import models,transaction
import datetime
class Registration(models.Model):
    name_of_child = models.CharField(max_length=100)
    dob = models.DateField(null=True, blank=True)  # Added dob field
    age = models.JSONField()
    sex = models.CharField(max_length=10)
    date = models.DateField(auto_now_add=True)
    mother_name = models.CharField(max_length=100, blank=True)
    father_name = models.CharField(max_length=100, blank=True)
    guardian_name= models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    mother_phone_number = models.CharField(max_length=15, blank=True) 
    father_phone_number = models.CharField(max_length=15, blank=True) 
    reason_for_visit = models.JSONField()
    duration_of_symptoms = models.TextField(blank=True, null=True)
    previous_treatment_done = models.TextField(blank=True, null=True)
    source_of_referral = models.JSONField(blank=True)  # Stores source of referral data as JSON
    registration_number = models.CharField(max_length=20, unique=True, blank=True)
    def save(self, *args, **kwargs):
        # Check if registration number is not already set
        if not self.registration_number:
            current_year = datetime.datetime.now().year
            # Use a database transaction to ensure atomicity
            with transaction.atomic():
                # Fetch the last registration object, lock the row, and ensure no other transaction can modify it
                last_reg = Registration.objects.select_for_update().order_by('id').last()
                if last_reg:
                    # Extract and increment the number from the last registration
                    reg_no = last_reg.registration_number.split('/')[1]
                    new_reg_no = int(reg_no) + 1
                else:
                    # If no registrations exist, start numbering from 1
                    new_reg_no = 1
                # Generate the new registration number in the format MDC/xxx/current_year
                self.registration_number = f'MDC/{new_reg_no:03}/{current_year}'
        # Call the parent class's save method to save the object in the database
        super(Registration, self).save(*args, **kwargs)


class PatientAssessment(models.Model):
    billing_no = models.CharField(max_length=20, unique=True, blank=True, null=True)
    registration_number = models.CharField(max_length=255)
    patient_name = models.CharField(max_length=255)
    age = models.JSONField()
    sex = models.CharField(max_length=10)
    father_phone_number = models.CharField(max_length=15, blank=True)
    mother_phone_number = models.CharField(max_length=15, blank=True)
    assessments = models.JSONField()  
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, blank=True)
    discount_remarks = models.CharField(max_length=1200, blank=True)
    finalAmount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    date = models.DateTimeField(auto_now_add=True)
    paymentMethod = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        if not self.billing_no:
            from .views import get_latest_billing_no
            latest_billing_no = get_latest_billing_no(None).content.decode()
            self.billing_no = latest_billing_no['billing_no']
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Assessment for {self.patient_name}"

    
#login
class Login(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)

from django.db import models
class EmployeeRegistration(models.Model):
    empid= models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  # Store hashed password in production
    confirmpassword = models.CharField(max_length=255)
    def __str__(self):
        return self.name
    
from django.db import models
class DevelopmentalTask(models.Model):
    age = models.JSONField()
    task = models.CharField(max_length=255)
    value = models.IntegerField()
    def __str__(self):
        return f"{self.age} - {self.task}"
    
from django.db import models
class PediatricAssessment(models.Model):
    name = models.CharField(max_length=100)
    age = models.JSONField()
    dob = models.DateField()
    concerns = models.TextField()
    antenatalHistory = models.TextField()  # Match with frontend
    antenatalComplications = models.TextField()  # Match with frontend
    birthDetails = models.TextField()  # Match with frontend
    neonatalDetails = models.TextField()  # Match with frontend
    familyHistory = models.TextField()  # Match with frontend
    developmentalHistory = models.JSONField()  # Store the array from frontend
    regression = models.TextField()
    generalExamination = models.TextField()
    builtNourishment = models.TextField()
    previousMedications = models.TextField()
    neonatalReflexes = models.TextField()
    cnsExamination = models.TextField()
    hearingVision = models.TextField()
    toneReflex = models.TextField()
    bowelBladder = models.TextField()
    specificConcerns = models.TextField()
    threeItems = models.TextField()
    threePoints = models.TextField()
    threeActivity = models.TextField()
    interpretationRecommendation = models.TextField()
    def __str__(self):
        return self.name
    
class SkillTestResult(models.Model):
    registration_number = models.CharField(max_length=50)
    patient_name = models.CharField(max_length=100)
    age = models.JSONField()
    sex = models.CharField(max_length=10)
    data = models.JSONField()  # Store JSON data in this field (for relational DB)
    date = models.DateField()
    def __str__(self):
        return f"Skill Test for {self.patient_name} ({self.registration_number})"
    

class TherapyBilling(models.Model):
    billing_no = models.CharField(max_length=20, unique=True, blank=True, null=True)
    registration_number = models.CharField(max_length=20,blank=True)
    name = models.CharField(max_length=100)  
    nameoftherapy = models.JSONField()
    therapy_charge = models.FloatField(blank=True, default=0.0)
    discount = models.FloatField(blank=True, default=0.0)
    discount_remarks = models.CharField(max_length=1200, blank=True)
    adjusted_charge = models.FloatField(blank=True, default=0.0)
    amount_paid = models.FloatField(blank=True, default=0.0)
    remaining_amount = models.FloatField(blank=True, default=0.0)
    payment_type = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=100, blank=True)
    consultant_doctor = models.JSONField()  
    age = models.JSONField()
    sex = models.CharField(max_length=10)
    father_phone_number = models.CharField(max_length=15, blank=True)   
    mother_phone_number = models.CharField(max_length=15, blank=True) 
    date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.billing_no:
            from .views import get_latest_billing_no
            latest_billing_no = get_latest_billing_no(None).content.decode()
            self.billing_no = latest_billing_no['billing_no']
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Billing No: {self.billing_no} - {self.name}"

    
from django.db import models
class MCHATResponse(models.Model):
    registration_number= models.CharField(max_length=255)
    patient_name = models.CharField(max_length=255)
    age = models.JSONField()
    sex = models.CharField(max_length=255)
    question = models.JSONField()  # Store responses as JSON
    score = models.IntegerField()
    riskLevel = models.CharField(max_length=255)
    date=models.DateField()
    def __str__(self):
        return f"{self.patient_name} - {self.age} - {self.sex}"
    
class ReferralDoctor(models.Model):
    doctor_name = models.CharField(max_length=100)
    hospital_name = models.CharField(max_length=100)
    area = models.CharField(max_length=100,blank=True)
    city = models.CharField(max_length=100,blank=True)
    district = models.CharField(max_length=100,blank=True)
    phone_number = models.CharField(max_length=15,blank=True)
    def __str__(self):
        return self.doctor_name
    

from django.db import models

class ChildLanguageAssessment(models.Model):
    childName = models.CharField(max_length=100)
    age = models.CharField(max_length=100)
    gender = models.TextField(max_length=100)  
    dateOfAssessment = models.DateField()
    complaint = models.TextField()
    onsetproblem = models.TextField()
    natureproblem = models.TextField()
    medicalhistory = models.TextField()
    natalhistory = models.JSONField() # JSON field for storing nested data
    familyhistory = models.TextField()  # Assuming a simple text for family history
    developmentalhistory = models.JSONField()  # JSON field for storing developmental history
    socialemotionalbehavior = models.JSONField() # JSON field for storing social/emotional behavior
    prerequisitesforspeech = models.JSONField()  # JSON field for prerequisites for speech
    oralperipheralmechanism = models.JSONField()  # JSON field for oral peripheral mechanism
    vegetativeskills = models.JSONField() # JSON field for vegetative skills
    communicationprofile = models.JSONField()  # JSON field for communication profile   
    testadministered = models.TextField()  # Text field for test administered
    provisionaldiagnosis = models.TextField()  # Text field for provisional diagnosis
    recommendation = models.TextField()  # Text field for recommendations
    
    def __str__(self):
        return self.childName
    
  # models.py

from django.db import models

class DevelopmentalScreeningTask(models.Model):
    patient_name = models.CharField(max_length=255)
    age = models.CharField(max_length=50, default="N/A")
    gender = models.CharField(max_length=50, default="N/A")
    CA = models.CharField(max_length=20, default="0 months")  # Added max_length
    DA = models.CharField(max_length=20, default="0 months")  # Added max_length
    dq_value = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    dq_classify = models.CharField(max_length=255, default="Nil")
    date = models.DateTimeField()  # Ensure the date field is defined

    # Grouped tasks by age group (using a JSONField for flexibility)
    tasks = models.JSONField()

    def __str__(self):
        return f"{self.patient_name} - {self.age}"


from django.db import models

# For table1, table2, etc.
class CBCL(models.Model):
    childName = models.CharField(max_length=255)
    age = models.JSONField()  # Store age as a JSON object: { "year": 5, "months": 3, "days": 20 }
    gender = models.CharField(max_length=10)
    dateOfAssessment = models.DateField()

    # Table fields (each as JSONField or specific field types as needed)
    table1 = models.JSONField(default=dict)
    table2 = models.JSONField(default=dict)
    table3 = models.JSONField(default=dict)
    table4 = models.JSONField(default=dict)
    table5 = models.JSONField(default=dict)
    table6 = models.JSONField(default=dict)
    table7 = models.JSONField(default=dict)

    def __str__(self):
        return self.patient_name


# models.py
from django.db import models

class ConsultingDoctor(models.Model):
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
