from rest_framework.decorators import api_view , permission_classes
from rest_framework.response import Response
from rest_framework import status
from ..models import MCHATResponse
from ..serializers import MCHATResponseSerializer
from ..auth.permissions import SkipPermissionsIfDisabled
from pyauth.auth import HasRoleAndDataPermission


@api_view(['POST'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def saveMCHATResponses(request):
    """
    Save M-CHAT responses for a patient, including the calculated risk level and total score.
    """
    data = request.data

    # Extract patient details
    registration_number= data.get('patient', {}).get('registration_number', 'Unknown')
    patient_name = data.get('patient', {}).get('name', 'Unknown')
    age = data.get('patient', {}).get('age', 'Unknown')
    sex = data.get('patient', {}).get('sex', 'Unknown')

    # Extract responses
    responses = data.get('responses', [])
    
    if not responses:
        return Response({"error": "No responses provided"}, status=status.HTTP_400_BAD_REQUEST)

    # Create the question list with all responses
    question_list = [
        {
            "question_no": response_data["question_no"],
            "question_text": response_data["question_text"],
            "answer": response_data["answer"],
            "score": response_data.get("score", 0)
        }
        for response_data in responses
    ]

    # Extract total score and risk level from the payload
    total_score = data.get('totalScore', 0)
    risk_level = data.get('riskLevel', 'Unknown')

    # Prepare the complete data object to save
    data_to_save = {
        'registration_number': registration_number,
        'patient_name': patient_name,
        'age': age,
        'sex': sex,
        'question': question_list,  # List of all questions and answers
        'score': total_score,  # Store the provided total score
        'riskLevel': risk_level  # Store the provided risk level
    }

    # Serialize and save
    serializer = MCHATResponseSerializer(data=data_to_save)

    if serializer.is_valid():
        serializer.save()
        return Response({"message": "All responses saved successfully"}, status=status.HTTP_201_CREATED)
    else:
        return Response({"error": "Failed to save responses", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from ..models import MCHATResponse
from ..serializers import MCHATResponseSerializer

@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def getMCHATResponse(request, registration_number):
    """
    Fetch M-CHAT-R responses for a given patient using their registration number.
    """
    try:
        response = MCHATResponse.objects.get(registration_number=registration_number)
        serializer = MCHATResponseSerializer(response)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except MCHATResponse.DoesNotExist:
        return Response({"error": "No data found for this registration number"}, status=status.HTTP_404_NOT_FOUND)