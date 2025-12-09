"""
URL configuration for the core app.
"""
from rest_framework.routers import DefaultRouter

from core import views


router = DefaultRouter()
router.register("locations", views.LocationViewSet, basename="location")
router.register("factions", views.FactionViewSet, basename="faction")
router.register("items", views.ItemViewSet, basename="item")

urlpatterns = router.urls
