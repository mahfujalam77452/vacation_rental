from django.shortcuts import render
from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import SearchForm
from .models import Location,Property
from .serializers import AutocompleteQuerySerializer,SuggestionSerializer
from django.core.paginator import Paginator
from django.db.models import Q,Case,IntegerField,When

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


def property_list(request):

    form = SearchForm(request.GET or None)

    properties = Property.objects.none()

    search_type = "text"

    if form.is_valid():

        q = form.cleaned_data["q"]

        search_type = form.cleaned_data["search_type"]
        object_id = form.cleaned_data.get("object_id")

        qs = (
            Property.objects.filter(is_active=True)
            .select_related("location")
            .prefetch_related("images")
        )

        ordering = ["-is_featured","-created_at","id"]

        if search_type == "location":
            # all property of selected location
            qs = qs.filter(location_id=object_id)

        elif search_type == "property":
            # All property with this property name

            selected = Property.objects.filter(id=object_id).first()

            if selected:

                qs = qs.filter(title__iexact=selected.title).annotate(
                    # Clicked property will apear first
                    is_selected = Case(
                        When(id=object_id, then = 0),
                        default = 1,
                        output_field = IntegerField()
                    )
                )

                ordering = ["is_selected","location__name","id"]
            else:
                qs = qs.none()

        else:
            #for day 3 semantics
            pass

        
        properties = qs.order_by(*ordering)

    paginator = Paginator(properties,6)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()

    params.pop("page",None)

    return render(
        request,"property_app/list.html",{
            "form":form,
            "page_obj":page_obj,
            "total":paginator.count,
            "search_type":search_type,
            "query_string":params.urlencode(),
        }
    )