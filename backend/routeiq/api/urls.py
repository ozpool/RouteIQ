from django.urls import path

from routeiq.api import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("geocode", views.geocode, name="geocode"),
    path("trips/plan", views.plan_trip, name="plan-trip"),
    path("trips/heatmap", views.corridor_heatmap, name="corridor-heatmap"),
]
