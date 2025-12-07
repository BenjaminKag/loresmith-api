from rest_framework.routers import DefaultRouter

from core import views

router = DefaultRouter()
router.register("locations", views.LocationViewSet, basename="location")

urlpatterns = router.urls
