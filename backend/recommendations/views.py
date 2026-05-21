from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response




# test view to check connection to API
@api_view(["POST"])
def recommend_track(request):
    return Response({
        "recommended_track": {
            "title": "Midnight City",
            "artist": "M83",
            "reason": "Selected as a mock result based on your recent listening session."
        }
    })
