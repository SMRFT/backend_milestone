from django.urls import path
from . import views 
from .views import pediatric_assessment_list,get_patients_report
from .Views import Security ,patientdetails ,cbcl,consultingdoctors,invoice,referals,mchat,therapybilling,childlanguage,developmentalscreeningtask


urlpatterns = [
    path('register/', patientdetails.create_registration, name='register'), 
    path('next-registration-number/', patientdetails.get_latest_registration_number, name='next_registration_number'),
    path('all-assessments/', patientdetails.get_all_assessments, name='all-assessments'),
    path('all-patient/', patientdetails.get_all_patients, name='all-patients'),
    path('save-assessments/', patientdetails.save_assessments, name='save-assessments'),   
    path('login/',Security.LoginView,name='LoginView'),
    path('developmental-tasks/', developmentalscreeningtask.DevelopmentalTask, name='DevelopmentalTask'),
    path('get-assessments/',patientdetails.get_assessments, name='get-assessments'),
    path('pediatric-assessment/',views.PediatricAssessment, name='pediatric-assessment'),
    path('save-patient-skill/', views.save_patient_skilltest, name='save-patient-skill'),
    path('pediatric_assessment_list/', pediatric_assessment_list, name='pediatric_assessment_list'),
    path('reg_no/<str:prefix>/<str:id>/<str:year>/', patientdetails.get_patient_by_registration, name='get_patient_by_registration'),
    path('all-patients/', get_patients_report, name='pediatric_assessment_list'),
    path('therapy_billing/', therapybilling.therapy_billing, name='therapy_billing'),   
    path('pendingPayment/', invoice.pendingPayment, name='pendingPayment'),
    path('updatePayment/', invoice.update_payment, name='update_payment'),
    path('get-latest-billing-no/', invoice.get_latest_billing_no,name='get_latest_billing_no'),
    path('employeeregistration/', Security.employeeregistration,name='employeeregistration'),
    path('get_patient_assessments/', views.get_patient_assessments, name='get_patient_assessments'),
    path('referrals/', referals.get_referrals, name='get_referrals'),
    path('therapy-reports/', therapybilling.get_therapy_reports, name='therapy-reports'),
    path('save-mchat-response/', mchat.saveMCHATResponses, name='save-mchat-response'),
    path('get-mchat/<path:registration_number>/', mchat.getMCHATResponse, name='get-mchat-response'),
    path("referral-doctor/register/", referals.register_referral_doctor, name="register-referral-doctor"),
    path("referral-doctor/list/", referals.get_referral_doctors, name="list-referral-doctors"),
    path('developmental-screening-tasks/', developmentalscreeningtask.save_developmental_screening_tasks, name='save_developmental_screening_tasks'),
    path('get-tasks/', developmentalscreeningtask.get_developmental_screening_tasks, name='get_tasks'),
    path('get-tasks/<str:patient_name>/', developmentalscreeningtask.get_developmental_screening_tasks, name='get_tasks_by_patient'),   
    path('child_language_reports/', childlanguage.get_childlanguage_reports, name='get_childlanguage_reports'),
    path('childspeechassessment/', childlanguage.child_language_assessment, name='child_language_assessment'),
    path('CBCLgirlsassessment/', cbcl.submit_cbcl, name='submit_cbcl'),
    path('get-cbcl/', cbcl.get_cbcl_data, name='get_all_cbcl'),
    path('get-cbcl/<str:childName>/', cbcl.get_cbcl_data, name='get_cbcl_by_patient'),
    path('save-consulting-doctor/', consultingdoctors.save_consulting_doctor, name='save_consulting_doctor'),
    path('get-consulting-doctors/', consultingdoctors.get_consulting_doctors, name='get_consulting_doctors'),
]
