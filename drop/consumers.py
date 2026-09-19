import json
from channels.generic.websocket import AsyncWebsocketConsumer

class SignalingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'slinger_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        
        # Send message to room group, excluding the sender
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'signaling_message',
                'message': data,
                'sender_channel_name': self.channel_name
            }
        )

    # Receive message from room group
    async def signaling_message(self, event):
        message = event['message']
        sender_channel_name = event['sender_channel_name']

        # Don't send the message back to the sender
        if self.channel_name != sender_channel_name:
            # Send message to WebSocket
            await self.send(text_data=json.dumps(message))
