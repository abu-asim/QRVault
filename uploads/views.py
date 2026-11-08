import os
import mimetypes
import qrcode

from datetime import timedelta
from io import BytesIO

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, FileResponse
from django.urls import reverse
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction
from django.utils import timezone

from .models import UploadedFile


MAX_FILE_SIZE = 100 * 1024 * 1024
MAX_FILES = 10

ALLOWED_EXTENSIONS = {
    '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp',
    '.mp4', '.mov',
    '.doc', '.docx', '.xls', '.xlsx',
    '.ppt', '.pptx', '.txt', '.zip'
}

PREVIEW_TYPES = {
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'application/pdf'
}

# Allowed expiry options
EXPIRY_OPTIONS = {
    '1h': timedelta(hours=1),
    '24h': timedelta(hours=24),
    '7d': timedelta(days=7)
}


# Homepage
def home(request):
    return render(request, 'home.html')


# File Upload API
@require_POST
def upload_files(request):

    uploaded_files = request.FILES.getlist('files')

    # Validate files
    if not uploaded_files:
        return JsonResponse({
            'success': False,
            'message': 'Please select at least one file.'
        }, status=400)

    if len(uploaded_files) > MAX_FILES:
        return JsonResponse({
            'success': False,
            'message': 'Maximum 10 files allowed.'
        }, status=400)

    # Validate expiry option
    expiry_option = request.POST.get('expiry', '24h')

    if expiry_option not in EXPIRY_OPTIONS:
        return JsonResponse({
            'success': False,
            'message': 'Invalid expiry option selected.'
        }, status=400)

    # Calculate expiry on the server
    expires_at = timezone.now() + EXPIRY_OPTIONS[expiry_option]

    # Validate file types and sizes
    for file in uploaded_files:

        extension = os.path.splitext(file.name)[1].lower()

        if extension not in ALLOWED_EXTENSIONS:
            return JsonResponse({
                'success': False,
                'message': f'Unsupported file type: {file.name}'
            }, status=400)

        if file.size > MAX_FILE_SIZE or file.size == 0:
            return JsonResponse({
                'success': False,
                'message': f'Invalid file size: {file.name}'
            }, status=400)

    results = []

    saved_files = []

    try:
        with transaction.atomic():

            for file in uploaded_files:

                content_type = (
                    mimetypes.guess_type(file.name)[0]
                    or 'application/octet-stream'
                )

                uploaded = UploadedFile.objects.create(
                    file=file,
                    original_name=file.name,
                    file_size=file.size,
                    content_type=content_type,
                    expires_at=expires_at
                )

                saved_files.append(uploaded)

                share_path = reverse(
                    'file_access',
                    kwargs={'file_id': uploaded.id}
                )

                share_url = request.build_absolute_uri(share_path)

                qr_path = reverse(
                    'qr_code',
                    kwargs={'file_id': uploaded.id}
                )

                qr_url = request.build_absolute_uri(qr_path)

                results.append({
                    'id': str(uploaded.id),
                    'name': uploaded.original_name,
                    'size': uploaded.file_size,
                    'share_url': share_url,
                    'qr_url': qr_url,
                    'expires_at': uploaded.expires_at.isoformat()
                })

    except Exception:

        # Remove physical files if database transaction fails
        for uploaded in saved_files:
            try:
                uploaded.file.delete(save=False)
            except Exception:
                pass

        return JsonResponse({
            'success': False,
            'message': 'Upload failed. Please try again.'
        }, status=500)

    return JsonResponse({
        'success': True,
        'message': 'Files uploaded successfully!',
        'files': results
    })


# QR Code Generation
@require_GET
def qr_code(request, file_id):

    uploaded = get_object_or_404(
        UploadedFile,
        id=file_id
    )

    # Prevent QR generation for expired files
    if is_file_expired(uploaded):
        return HttpResponse('File expired.', status=410)

    qr_path = reverse(
        'file_access',
        kwargs={'file_id': uploaded.id}
    )

    share_url = request.build_absolute_uri(qr_path)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )

    qr.add_data(share_url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    buffer = BytesIO()
    image.save(buffer, format='PNG')

    return HttpResponse(
        buffer.getvalue(),
        content_type='image/png'
    )


# Check File Expiry
def is_file_expired(uploaded):

    return timezone.now() >= uploaded.expires_at


# File Access Page
@require_GET
def file_access(request, file_id):

    uploaded = get_object_or_404(
        UploadedFile,
        id=file_id
    )

    if is_file_expired(uploaded):

        return render(
            request,
            'file_access.html',
            {'expired': True},
            status=410
        )

    file_type = uploaded.content_type

    is_image = file_type.startswith('image/')
    is_pdf = file_type == 'application/pdf'

    preview_url = None

    if file_type in PREVIEW_TYPES:

        preview_url = reverse(
            'file_preview',
            kwargs={'file_id': uploaded.id}
        )

    file_size = uploaded.file_size

    if file_size < 1024 * 1024:
        file_size = f'{file_size / 1024:.2f} KB'
    else:
        file_size = f'{file_size / (1024 * 1024):.2f} MB'

    context = {
        'file': uploaded,
        'file_size': file_size,
        'file_type': file_type,
        'preview_url': preview_url,
        'is_image': is_image,
        'is_pdf': is_pdf,
        'expired': False
    }

    return render(
        request,
        'file_access.html',
        context
    )


# Secure File Preview
@require_GET
def file_preview(request, file_id):

    uploaded = get_object_or_404(
        UploadedFile,
        id=file_id
    )

    if is_file_expired(uploaded):
        return HttpResponse('File expired.', status=410)

    if uploaded.content_type not in PREVIEW_TYPES:
        return HttpResponse('Preview not supported.', status=415)

    if not uploaded.file:
        return HttpResponse('File unavailable.', status=404)

    response = FileResponse(
        uploaded.file.open('rb'),
        content_type=uploaded.content_type
    )

    response['X-Content-Type-Options'] = 'nosniff'

    return response


# Download File
@require_GET
def file_download(request, file_id):

    uploaded = get_object_or_404(
        UploadedFile,
        id=file_id
    )

    if is_file_expired(uploaded):
        return HttpResponse('File expired.', status=410)

    if not uploaded.file:
        return HttpResponse('File unavailable.', status=404)

    response = FileResponse(
        uploaded.file.open('rb'),
        as_attachment=True,
        filename=uploaded.original_name
    )

    response['X-Content-Type-Options'] = 'nosniff'

    return response