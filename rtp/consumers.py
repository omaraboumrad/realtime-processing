import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class ImageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join the image updates group
        await self.channel_layer.group_add("image_updates", self.channel_name)
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {"type": "connection", "message": "Hello!"}
            )
        )

    async def disconnect(self, close_code):
        # Leave the image updates group
        await self.channel_layer.group_discard("image_updates", self.channel_name)

    @database_sync_to_async
    def get_images_from_db(self):
        """
        Get images from database (sync operation)
        """
        from .models import Image

        images = Image.objects.all()
        return [
            {
                "id": img.id,
                "status": img.status,
                "uploaded_at": img.uploaded_at.isoformat(),
                "original_image": (
                    img.original_image.url if img.original_image else None
                ),
                "processed_image": (
                    img.processed_image.url if img.processed_image else None
                ),
                "filename": (
                    img.original_image.name.split("/")[-1]
                    if img.original_image
                    else None
                ),
            }
            for img in images
        ]

    async def receive(self, text_data):
        """
        Receive message from WebSocket
        """
        data = json.loads(text_data)
        message_type = data.get("type", "")

        if message_type == "ping":
            # Respond to ping with pong
            await self.send(
                text_data=json.dumps({"type": "pong", "message": "Pong from server"})
            )
        elif message_type == "get_images":
            # Send current images list
            images_data = await self.get_images_from_db()
            await self.send(
                text_data=json.dumps({"type": "images_list", "images": images_data})
            )

    async def image_update(self, event):
        """
        Receive message from channel layer and send to WebSocket
        """
        message = event["message"]
        response = {"type": "image_update", "message": message}

        # Include additional data if present
        if "image_id" in event:
            response["image_id"] = event["image_id"]
        if "processed_image" in event:
            response["processed_image"] = event["processed_image"]

        await self.send(text_data=json.dumps(response))
