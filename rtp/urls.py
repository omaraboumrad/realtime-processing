from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from rtp import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="index"),
    path("upload/", views.upload_image, name="upload_image"),
    path("process/<int:pk>/", views.process_image_view, name="process_image"),
    path("process-all/", views.process_all_images, name="process_all_images"),
    path("images/", views.get_images, name="get_images"),
    path("delete/<int:pk>/", views.delete_image, name="delete_image"),
    path("replay/<int:pk>/", views.replay_image, name="replay_image"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
