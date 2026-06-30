from djongo import models
from djongo.models import ObjectIdField
from django.db import transaction

import datetime
from django.utils.timezone import now
from django.utils import timezone

class AuditModel(models.Model):
    created_by = models.CharField(max_length=100, blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    lastmodified_by = models.CharField(max_length=100, blank=True, null=True)
    lastmodified_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True

class Registration(AuditModel):
    name_of_child = models.CharField(max_length=100)
    dob = models.DateField(null=True, blank=True)  # Added dob field
    age = models.JSONField()
    sex = models.CharField(max_length=10)
    date = models.DateField(auto_now_add=True)
    mother_name = models.CharField(max_length=100, blank=True)
    father_name = models.CharField(max_length=100, blank=True)
    guardian_name= models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    mail_id = models.TextField(blank=True)
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
    class Meta:
        db_table = "milestone_backend_registration" 

class PatientAssessment(AuditModel):
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
            from .Views.invoice import get_latest_billing_no
            latest_billing_no = get_latest_billing_no(None).content.decode()
            self.billing_no = latest_billing_no['billing_no']
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Assessment for {self.patient_name}"

class EmployeeRegistration(AuditModel):
    empid= models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  # Store hashed password in production
    confirmpassword = models.CharField(max_length=255)
    def __str__(self):
        return self.name
    

class DevelopmentalTask(AuditModel):
    age = models.JSONField()
    task = models.CharField(max_length=255)
    value = models.IntegerField()
    def __str__(self):
        return f"{self.age} - {self.task}"

class PediatricAssessment(AuditModel):
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
    
class SkillTestResult(AuditModel):
    registration_number = models.CharField(max_length=50)
    patient_name = models.CharField(max_length=100)
    age = models.JSONField()
    sex = models.CharField(max_length=10)
    data = models.JSONField()  # Store JSON data in this field (for relational DB)
    date = models.DateField()
    def __str__(self):
        return f"Skill Test for {self.patient_name} ({self.registration_number})"
    

class TherapyBilling(AuditModel):
    registration_number = models.CharField(max_length=20)
    billing_no = models.CharField(max_length=50, unique=True)

    # Linking to attendance
    attendance_date = models.DateField()
    bill_date = models.DateField(auto_now_add=True)

    # Charges
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Payment
    payment_type = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Billing No: {self.billing_no} - {self.registration_number}"

    class Meta:
        verbose_name = "Therapy Billing"
        verbose_name_plural = "Therapy Billings"
    

class OthersBilling(AuditModel):
    billing_no = models.CharField(max_length=20, unique=True, blank=True, null=True)
    registration_number = models.CharField(max_length=20, blank=True)
    name = models.CharField(max_length=100)
    age = models.JSONField()
    sex = models.CharField(max_length=10)
    father_phone_number = models.CharField(max_length=15, blank=True)
    mother_phone_number = models.CharField(max_length=15, blank=True)
    others_items = models.JSONField(default=list, blank=True)  # Array to store {description, amount} objects
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    payment_method = models.CharField(max_length=100, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Billing No: {self.billing_no} - {self.name}"
    

class MCHATResponse(AuditModel):
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
    
class ReferralDoctor(AuditModel):
    doctor_name = models.CharField(max_length=100)
    referral_id = models.CharField(max_length=10, blank=True, null=True)  # Make it optional first
    sex = models.CharField(max_length=20, blank=True, null=True)  # Make it optional first  
    email = models.CharField(max_length=100, blank=True, null=True)  # Use CharField instead of EmailField initially
    hospital_name = models.CharField(max_length=100)
    area = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.referral_id:
            # Simple auto-increment logic
            last_id = ReferralDoctor.objects.count()
            self.referral_id = f"{last_id + 1:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.doctor_name





class ChildLanguageAssessment(AuditModel):
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
    


class DevelopmentalScreeningTask(AuditModel):
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



class CBCL(AuditModel):
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



class ConsultingDoctor(AuditModel):
    employee_id = models.CharField(max_length=100,blank=True)
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

# models.py
from datetime import date

class PatientAttendance(AuditModel):
    registration_number = models.CharField(max_length=50)
    attendance_date = models.DateField()  # Attendance Date
    session = models.IntegerField()
    # Therapy Details
    therapy_details = models.JSONField(default=list, blank=True)
    therapy_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Discount
    discount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_remarks = models.CharField(max_length=500, blank=True)

    # Not Attending
    not_attending = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    not_attending_details = models.JSONField(default=list, blank=True)
    not_attending_remarks = models.CharField(max_length=500, blank=True)

    # Extra Attending
    extra_attending = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    extra_attending_details = models.JSONField(default=list, blank=True)
    extra_attending_remarks = models.CharField(max_length=500, blank=True)

    # Final Billing Info
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bill_details = models.JSONField(default=list, blank=True)

    # Consultant
    consultant_doctor = models.JSONField(default=list, blank=True)

    # System Controls
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.registration_number} - {self.attendance_date}"

    class Meta:
        verbose_name = "Patient Attendance"
        verbose_name_plural = "Patient Attendances"

class HistoryRecordingSheet(AuditModel):
    registration_number = models.CharField(max_length=100,primary_key=True)
    identification_data = models.JSONField()
    demographic_data = models.JSONField()
    presenting_complaints = models.JSONField()
    history_of_present_illness= models.JSONField()
    family_history=models.JSONField()
    personal_history=models.JSONField()
    natalandneanatal_history=models.JSONField()
    postnatal_history=models.JSONField()
    developmental_history=models.JSONField()
    scholastic_history=models.JSONField()
    play_history=models.JSONField()
    treatment_history= models.CharField(max_length=5000)
    general_history=models.JSONField()
    OverAllImpression = models.CharField(max_length=5000)
    OverAllSummary = models.CharField(max_length=5000)
    Recommendation = models.CharField(max_length=5000)

class ClinicalPsychologyAssessment(AuditModel):
    assessment_date = models.DateField()
    registrationNumber = models.CharField(max_length=500, blank=True)
    patientName = models.CharField(max_length=500, blank=True)
    # Store as JSON list
    behaviour_problems = models.JSONField(default=list, blank=True)
    # General Temperament as JSON
    general_temperament = models.JSONField(default=dict, blank=True)
    # Behavioral Observation as JSON
    behavioral_observation = models.JSONField(default=dict, blank=True)
    # Assessment Tests as JSON
    assessments_used = models.JSONField(default=dict, blank=True)
    impression = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-assessment_date']
    def __str__(self):
        return f"{self.patientName} - {self.assessment_date}"
    
class OccupationalTherapyAssessment(AuditModel):
    assessment_date = models.DateField()
    registrationNumber = models.CharField(max_length=500, blank=True)
    patientName = models.CharField(max_length=500, blank=True)
    motor_skills = models.JSONField(default=dict, blank=True)
    handwriting_skills = models.JSONField(default=dict, blank=True)
    cognitive_concepts = models.JSONField(default=dict, blank=True)
    visual_perceptual_skills = models.JSONField(default=dict, blank=True)
    sensory_evaluation = models.JSONField(default=dict, blank=True)
    adl_evaluation = models.JSONField(default=dict, blank=True)
    assessments_used = models.JSONField(default=dict, blank=True)
    impression = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-assessment_date']
    def __str__(self):
        return f"{self.patientName} - {self.assessment_date}"
    
class SpeechTherapyAssessment(AuditModel):
    assessment_date = models.DateField()
    registrationNumber = models.CharField(max_length=500, blank=True)
    patientName = models.CharField(max_length=500, blank=True)
    oral_peripheral_mechanism = models.JSONField(default=dict, blank=True)
    oral_impression = models.TextField(blank=True)
    vegetative_skills = models.JSONField(default=dict, blank=True)
    speech_parameters = models.JSONField(default=dict, blank=True)
    communication_profile = models.JSONField(default=dict, blank=True)
    linguistic_profile = models.JSONField(default=dict, blank=True)
    assessments_used = models.JSONField(default=dict, blank=True)
    impression = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-assessment_date']
    def __str__(self):
        return f"{self.patientName} - {self.assessment_date}"
    
class PhysiotherapyAssessment(AuditModel):
    assessment_date = models.DateField()
    registrationNumber = models.CharField(max_length=100, blank=True)
    patientName = models.CharField(max_length=255, blank=True)
    on_observation = models.JSONField(default=dict, blank=True)
    tone = models.JSONField(default=dict, blank=True)
    motor_system = models.JSONField(default=dict, blank=True)
    clonus = models.JSONField(default=dict, blank=True)
    coordination = models.JSONField(default=dict, blank=True)
    pattern_and_position = models.JSONField(default=dict, blank=True)
    limb_length_discrepancy = models.JSONField(default=dict, blank=True)
    balance = models.JSONField(default=dict, blank=True)
    sensation = models.JSONField(default=dict, blank=True)
    assessments_used = models.JSONField(default=list, blank=True)
    impression = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-assessment_date']
    def __str__(self):
        return f"{self.patientName} - {self.assessment_date}"
    
class AssessmentAnalysis(AuditModel):
    registration_number = models.CharField(max_length=50)
    patient_name = models.CharField(max_length=100)
    age = models.CharField(max_length=10)
    sex = models.CharField(max_length=10)
    date = models.DateField()
    billing_no = models.CharField(max_length=50, primary_key=True)
    # Provisional Diagnosis
    provisional_diagnosis = models.TextField(blank=True, null=True)
    # Preferred Language
    preferred_language = models.JSONField(default=dict)
    # Home & Parenting
    home_modification = models.TextField(blank=True, null=True)
    parenting_modifications = models.TextField(blank=True, null=True)
    # Mapping Therapy
    mapping_therapy = models.JSONField(default=dict)
    # Session Numbers
    session_numbers = models.JSONField(default=dict)
    # Therapy Methods
    therapy_methods = models.JSONField(default=dict)
    def __str__(self):
        return f"{self.registration_number} - {self.patient_name}"

class GoalsAssessment(AuditModel):   
    _id = models.ObjectIdField(primary_key=True)

    registration_number = models.CharField(max_length=50)
    date = models.DateField()
    deadline = models.DateField()
    goals = models.JSONField(default=list, blank=True)
    parent_comments = models.TextField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    recommendations = models.TextField(blank=True, null=True)
    refference = models.CharField(max_length=500,blank=True, null=True)
    goalsphoto = models.JSONField(default=list, blank=True)
    goalsvideo = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ('registration_number', 'date')
        
    def __str__(self):
        return f"{self.registration_number} - {self.date}"
    
class leaveform(AuditModel):
    registration_number = models.CharField(max_length=50)
    leave_date = models.DateField()
    leave_reason = models.TextField(blank=True, null=True)
    leave_status = models.CharField(max_length=50,default="Pending")
    leave_approved_by = models.CharField(max_length=50,null=True, blank=True)
    leave_approved_date = models.DateField(null=True, blank=True)
    leave_reject_comments = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('registration_number', 'leave_date')
        db_table = 'milestone_backend_leaveform'
    def __str__(self):
        return f"{self.registration_number} - {self.leave_date}"

class DevelopmentGoals(AuditModel):
    _id = models.ObjectIdField()
    registration_number = models.CharField(max_length=50)
    date = models.DateField()
    development_goals = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.registration_number} - {self.date}"

def get_therapy_abbreviation(therapy_name):
    if not therapy_name:
        return "GN"
    name = str(therapy_name).lower().strip()
    if "occupational" in name or "ot" in name:
        return "OT"
    elif "cognitive" in name or "ct" in name:
        return "CT"
    elif "speech" in name or "st" in name:
        return "ST"
    elif "physio" in name or "pt" in name:
        return "PT"
    elif "art therapy" in name or "at" in name:
        return "AT"
    elif "early intervention" in name or "ei" in name:
        return "EI"
    elif "applied behavior" in name or "aba" in name:
        return "AT"
    elif "special education" in name:
        return "SE"
    elif "social training" in name:
        return "SC"
    elif "curriculum" in name:
        return "CC"
    elif "group therapy" in name:
        return "GT"
    else:
        words = name.split()
        if len(words) >= 2:
            return "".join(w[0].upper() for w in words[:2])
        return name[:2].upper()

class TherapyDetails(AuditModel):
    _id = models.ObjectIdField()
    therapy_name = models.CharField(max_length=255)
    therapy_id = models.CharField(max_length=10, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.therapy_id:
            count = TherapyDetails.objects.count()
            self.therapy_id = f"THP{count+1:03d}"
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = "milestone_backend_therapydetails"

class GoalDomain(AuditModel):
    _id = models.ObjectIdField()
    name = models.CharField(max_length=200)
    therapy_type = models.CharField(max_length=100) # Storing ID of TherapyDetails as string
    domain_no = models.CharField(max_length=20, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.domain_no:
            try:
                from bson import ObjectId
                if len(self.therapy_type) == 24:
                    therapy = TherapyDetails.objects.get(_id=ObjectId(self.therapy_type))
                    therapy_name = therapy.therapy_name
                else:
                    therapy_name = self.therapy_type
            except:
                therapy_name = self.therapy_type
                
            prefix = get_therapy_abbreviation(therapy_name)
            count = GoalDomain.objects.filter(therapy_type=self.therapy_type).count()
            self.domain_no = f"{prefix}{count+1:03d}"
        super().save(*args, **kwargs)

    def __str__(self): return self.name

class GoalLevel(AuditModel):
    _id = models.ObjectIdField()
    name = models.CharField(max_length=50) 
    level_id = models.CharField(max_length=10, blank=True)

    def save(self, *args, **kwargs):
        if not self.level_id:
            count = GoalLevel.objects.count()
            self.level_id = f"LVL{count+1:02d}"
        super().save(*args, **kwargs)

    def __str__(self): return self.name

class GoalLibrary(AuditModel):
    _id = models.ObjectIdField()
    goal_name = models.TextField()
    goal_no = models.CharField(max_length=20, blank=True)
    domain = models.CharField(max_length=100) # Storing ID as string
    therapy_type = models.CharField(max_length=100) # Storing ID as string
    level = models.CharField(max_length=100, blank=True, null=True) # Storing ID as string
    is_custom = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        from bson import ObjectId

        # 1. Normalize therapy_type to therapy_id
        if self.therapy_type:
            therapy_obj = None
            if len(self.therapy_type) == 24:
                try:
                    therapy_obj = TherapyDetails.objects.get(_id=ObjectId(self.therapy_type))
                except: pass
            if not therapy_obj:
                try:
                    therapy_obj = TherapyDetails.objects.get(therapy_id=self.therapy_type)
                except: pass
            if not therapy_obj:
                try:
                    therapy_obj = TherapyDetails.objects.get(therapy_name=self.therapy_type)
                except: pass
            if therapy_obj:
                self.therapy_type = therapy_obj.therapy_id

        # 2. Normalize domain to domain_no
        if self.domain:
            domain_obj = None
            if len(self.domain) == 24:
                try:
                    domain_obj = GoalDomain.objects.get(_id=ObjectId(self.domain))
                except: pass
            if not domain_obj:
                try:
                    domain_obj = GoalDomain.objects.get(domain_no=self.domain)
                except: pass
            if not domain_obj:
                try:
                    domain_obj = GoalDomain.objects.filter(name=self.domain, therapy_type=self.therapy_type).first()
                except: pass
            if not domain_obj:
                try:
                    domain_obj = GoalDomain.objects.filter(name=self.domain).first()
                except: pass
            if domain_obj:
                self.domain = domain_obj.domain_no

        # 3. Normalize level to level_id
        if self.level:
            level_obj = None
            if len(self.level) == 24:
                try:
                    level_obj = GoalLevel.objects.get(_id=ObjectId(self.level))
                except: pass
            if not level_obj:
                try:
                    level_obj = GoalLevel.objects.get(level_id=self.level)
                except: pass
            if not level_obj:
                try:
                    level_obj = GoalLevel.objects.get(name=self.level)
                except: pass
            if level_obj:
                self.level = level_obj.level_id

        # 4. Generate goal_no if empty
        if not self.goal_no:
            try:
                if len(self.therapy_type) == 24:
                    therapy = TherapyDetails.objects.get(_id=ObjectId(self.therapy_type))
                    therapy_name = therapy.therapy_name
                elif self.therapy_type.startswith("THP"):
                    therapy = TherapyDetails.objects.get(therapy_id=self.therapy_type)
                    therapy_name = therapy.therapy_name
                else:
                    therapy_name = self.therapy_type
            except:
                therapy_name = self.therapy_type
                
            prefix = get_therapy_abbreviation(therapy_name)
            count = GoalLibrary.objects.filter(therapy_type=self.therapy_type).count()
            self.goal_no = f"{prefix}GL{count+1:04d}"
            
        super().save(*args, **kwargs)

    def __str__(self): return self.goal_name

