from django.urls import path

from . import views

urlpatterns = [
    path("lookup/", views.EmployerLookupView.as_view(), name="employer-lookup"),
]
