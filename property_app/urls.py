from django.urls import path

from . import views

urlpatterns = [
    path("",views.home,name="home"),
    path("search/",views.property_list,name="property_list"),
    path("api/autocomplete/",views.AutocompleteAPIView.as_view(),name="api_autocomplete"),
    path("property/<slug:slug>/",views.property_detail,name="property_detail"),
]