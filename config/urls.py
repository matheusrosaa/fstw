from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]

handler404 = "core.views.base.erro_404"
handler403 = "core.views.base.erro_403"
