import os
import time
import random

from asgiref.sync import async_to_sync
from django.tasks import task
from django.utils import timezone

from PIL import Image as PILImage
from channels.layers import get_channel_layer
import numpy as np

from .models import Image


@task()
def process_image(image_id):
    """
    Background task to apply randomized color modifications to an image.
    """
    try:
        image = Image.objects.get(id=image_id)
        image.status = "processing"
        image.save()

        # Notify via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "image_updates",
            {"type": "image_update", "message": f"Processing image {image_id}..."},
        )

        # Simulate long-running task, you should remove this.
        # time.sleep(5)

        # Open the original image
        original_path = image.original_image.path
        pil_image = PILImage.open(original_path)

        # Convert to RGB if needed
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        # Convert to numpy array for pixel manipulation
        img_array = np.array(pil_image)

        # Generate random color shifts for each pixel
        random_shifts = np.random.randint(
            -100, 101, size=img_array.shape, dtype=np.int16
        )
        shifted_array = img_array.astype(np.int16) + random_shifts
        shifted_array = np.clip(shifted_array, 0, 255).astype(np.uint8)

        # Convert back to PIL Image
        modified_image = PILImage.fromarray(shifted_array)

        # Save the processed image
        processed_filename = f"processed_{os.path.basename(original_path)}"
        processed_path = os.path.join(
            os.path.dirname(original_path).replace("original", "processed"),
            processed_filename,
        )

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(processed_path), exist_ok=True)

        # Save the modified image
        modified_image.save(processed_path)

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
