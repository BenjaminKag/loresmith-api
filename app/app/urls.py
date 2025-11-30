from django.contrib import admin
from django.urls import path

# Optional DRF API setup (uncomment when creating an API)

# from django.urls import include
# from rest_framework.routers import DefaultRouter

# router = DefaultRouter()
# router.register("example", ExampleViewSet, basename="example")

urlpatterns = [
    path('admin/', admin.site.urls),
]

# urlpatterns += router.urls
