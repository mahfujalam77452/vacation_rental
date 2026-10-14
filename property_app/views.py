from django.shortcuts import render
from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import SearchForm
from .models import Location,Property
from .serializers import AutocompleteQuerySerializer,SuggestionSerializer


def home(request):
    return render(request,"property_app/home.html",{"form":SearchForm()})

def property_list(request):

    form = SearchForm(request.GET)

    if not form.is_valid():
        return HttpResponse(f"Invalid: {form.errors.as_json()}",status=400)
    return HttpResponse(f"OK:{form.cleaned_data}")


class AutocompleteAPIView(APIView):

    """GET /api/autocomplete/?q=flo -> Location and property suggestion """

    def get(self,request):

        query = AutocompleteQuerySerializer(data=request.query_params)

        query.is_valid(raise_exception=True)
        q = query.validated_data["q"]

        locations = Location.objects.filter(is_active=True,name__icontains=q)[:5]

        properties = (
            Property.objects.filter(is_active=True,title__icontains=q)
            .select_related("location")[:5]
        
        )

        results = [
            {"type":"location","id":location.id,"name":location.name} for location in locations
        ] + [
            {"type":"property","id":property.id,"name":property.title,"location":property.location.name}
            for property in properties
        ]

        return Response({"results": SuggestionSerializer(results,many=True).data})
