import os
import time
import random

from asgiref.sync import async_to_sync
from django.tasks import task
from django.utils import timezone

from PIL import Image as PILImage
from channels.layers import get_channel_layer

from .models import Image


@task()
def process_image(image_id):
    """
    Background task to convert an image to grayscale.
    """
    try:
        image = Image.objects.get(id=image_id)
        image.status = "processing"
        image.save()

        # Randomly choose delay between 3 and 5 seconds
        delay = random.randint(3, 5)

        # Notify via WebSocket with the actual delay
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "image_updates",
            {
                "type": "image_update",
                "message": f"Processing image {image_id} (delay: {delay}s)...",
            },
        )

        # Simulate long-running task
        time.sleep(delay)

        # Open the original image
        original_path = image.original_image.path
        pil_image = PILImage.open(original_path)

        # Convert to grayscale
        grayscale_image = pil_image.convert("L")

        # Save the processed image
        processed_filename = f"processed_{os.path.basename(original_path)}"
        processed_path = os.path.join(
            os.path.dirname(original_path).replace("original", "processed"),
            processed_filename,
        )

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(processed_path), exist_ok=True)

        # Save the grayscale image
        grayscale_image.save(processed_path)

        # Update the model
        image.processed_image = f"images/processed/{processed_filename}"
        image.status = "completed"
        image.processed_at = timezone.now()
        image.save()

        # Notify completion via WebSocket
        async_to_sync(channel_layer.group_send)(
            "image_updates",
            {
                "type": "image_update",
                "message": f"Image {image_id} processing completed!",
                "image_id": image_id,
                "processed_image": image.processed_image.url,
            },
        )

        return f"Successfully processed image {image_id}"

    except Image.DoesNotExist:
        return f"Image {image_id} not found"
    except Exception as e:
        # Handle errors
        if "image" in locals():
            image.status = "pending"
            image.save()
        return f"Error processing image {image_id}: {str(e)}"
