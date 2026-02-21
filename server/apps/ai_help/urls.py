from django.urls import path

from .views import ask

urlpatterns = [
    path("ai/ask/", ask, name="ai-ask"),
]
