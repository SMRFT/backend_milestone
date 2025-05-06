from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ..models import ChildLanguageAssessment
import json
from rest_framework.decorators import api_view , permission_classes
from rest_framework.response import Response
from ..models import ChildLanguageAssessment
from ..serializers import ChildLanguageAssessmentSerializer
from django.utils.dateparse import parse_date
from django.utils import timezone



from ..auth.permissions import SkipPermissionsIfDisabled
from pyauth.auth import HasRoleAndDataPermission

@csrf_exempt  # Disable CSRF check for this API endpoint (Optional, but you might need it for testing)
@api_view(['POST'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def child_language_assessment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Get the data from the request body
            child_name = data.get('childName')
            age = data.get('age')
            gender = data.get('gender')         
            date_of_assessment = data.get('dateOfAssessment')
            complaint = data.get('complaint')
            onsetproblem = data.get('onsetproblem')
            natureproblem = data.get('natureproblem')
            medicalhistory = data.get('medicalhistory')
            natalhistory = data.get('natalhistory')
            familyhistory = data.get('familyhistory')  
            developmentalhistory = data.get('developmentalhistory')  
            socialemotionalbehavior = data.get('socialemotionalbehavior')  
            prerequisitesforspeech = data.get('prerequisitesforspeech')  
            oralperipheralmechanism = data.get('oralperipheralmechanism')  
            vegetativeskills = data.get('vegetativeskills') 
            communicationprofile = data.get('communicationprofile')   
            testadministered = data.get('testadministered')  
            provisionaldiagnosis = data.get('provisionaldiagnosis') 
            recommendation = data.get('recommendation')  


            # Create a new ChildLanguageAssessment object
            assessment = ChildLanguageAssessment(
                childName=child_name,
                age=age,
                gender=gender,           
                dateOfAssessment=date_of_assessment,
                complaint=complaint,
                onsetproblem=onsetproblem,
                natureproblem=natureproblem,
                medicalhistory=medicalhistory,
                natalhistory=natalhistory, 
                familyhistory=familyhistory,  
                developmentalhistory=developmentalhistory,  
                socialemotionalbehavior=socialemotionalbehavior,  
                prerequisitesforspeech=prerequisitesforspeech,  
                oralperipheralmechanism=oralperipheralmechanism,  
                vegetativeskills=vegetativeskills, 
                communicationprofile=communicationprofile,   
                testadministered=testadministered,  
                provisionaldiagnosis=provisionaldiagnosis, 
                recommendation=recommendation,  
            )
            assessment.save()

            return JsonResponse({'message': 'Assessment submitted successfully!'}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid HTTP method'}, status=405)
    



@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_childlanguage_reports(request):
    # Extract the 'fromDate' and 'toDate' query parameters
    from_date_str = request.GET.get('fromDate')
    to_date_str = request.GET.get('toDate')

    # Parse the date strings to date objects
    from_date = parse_date(from_date_str) if from_date_str else None
    to_date = parse_date(to_date_str) if to_date_str else None

    # Get current date (for default filtering)
    current_date = timezone.now().date()

    # Filter the assessments by the provided date range or use current date as default
    assessments = ChildLanguageAssessment.objects.all()

    # If no date range is provided, filter for today's data
    if not from_date and not to_date:
        assessments = assessments.filter(dateOfAssessment=current_date)
    else:
        if from_date:
            assessments = assessments.filter(dateOfAssessment__gte=from_date)
        if to_date:
            assessments = assessments.filter(dateOfAssessment__lte=to_date)

    # Serialize and return the filtered data
    serializer = ChildLanguageAssessmentSerializer(assessments, many=True)
    return Response(serializer.data)





