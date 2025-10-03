from pathlib import Path

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Image
from .tasks import process_image

home = ListView.as_view(model=Image)


@csrf_exempt
@require_http_methods(["POST"])
def upload_image(request):
    if "image" not in request.FILES:
        return JsonResponse({"error": "No image provided"}, status=400)

    image = Image.objects.create(original_image=request.FILES["image"])

    return JsonResponse(
        {
            "id": image.id,
            "status": image.status,
            "message": "Image uploaded successfully",
            "original_image": image.original_image.url,
            "filename": Path(image.original_image.path).name,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def process_image_view(request, pk):
    image = get_object_or_404(Image, id=pk)

    if image.status == "completed":
        return JsonResponse({"error": "Image already processed"}, status=400)

    process_image.enqueue(pk)

    return JsonResponse(
        {
            "id": image.id,
            "status": "processing",
            "message": "Image processing started",
            "simulated_delay": "3-5s",
        }
    )


@require_http_methods(["GET"])
def get_images(request):
    images = [
        {
            "id": img.id,
            "status": img.status,
            "uploaded_at": img.uploaded_at.isoformat(),
            "original_image": img.original_image.url if img.original_image else None,
            "processed_image": img.processed_image.url if img.processed_image else None,
            "filename": (
                Path(img.original_image.path).name if img.original_image else None
            ),
        }
        for img in Image.objects.all()
    ]
    return JsonResponse({"images": images})


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_image(request, pk):
    image = get_object_or_404(Image, id=pk)
    image.delete()

    return JsonResponse({"id": pk, "message": "Image deleted successfully"})


@csrf_exempt
@require_http_methods(["POST"])
def replay_image(request, pk):
    original_image = get_object_or_404(Image, id=pk)

    # Create a new image record with the same original_image file
    new_image = Image.objects.create(original_image=original_image.original_image)

    return JsonResponse(
        {
            "id": new_image.id,
            "status": new_image.status,
            "message": "Image duplicated successfully",
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def process_all_images(request):
    # Get all pending images
    pending_images = Image.objects.filter(status="pending")

    image_ids = []
    for image in pending_images:
        process_image.enqueue(image.id)
        image_ids.append(image.id)

    return JsonResponse(
        {
            "count": len(image_ids),
            "image_ids": image_ids,
            "message": f"Started processing {len(image_ids)} image(s)",
            "simulated_delay": "3-5s",
        }
    )
