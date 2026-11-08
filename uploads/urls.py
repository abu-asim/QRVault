from django.urls import path
from uploads import views

urlpatterns = [

    path('', views.home, name='home'),

    path('api/upload/', views.upload_files, name='upload_files'),

    path(
        'api/qr/<uuid:file_id>/',
        views.qr_code,
        name='qr_code'
    ),

    path(
        'file/<uuid:file_id>/',
        views.file_access,
        name='file_access'
    ),

    path(
        'file/<uuid:file_id>/preview/',
        views.file_preview,
        name='file_preview'
    ),

    path(
        'file/<uuid:file_id>/download/',
        views.file_download,
        name='file_download'
    ),

]