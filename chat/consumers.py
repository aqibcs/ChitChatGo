import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Message, ChatGroup, Notification

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.chat_type = self.scope['url_route']['kwargs']['chat_type']
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        
        if self.chat_type == 'direct':
            # Direct chat room name is a combination of the two user IDs (sorted)
            user_ids = sorted([self.user.id, int(self.chat_id)])
            self.room_group_name = f'chat_direct_{user_ids[0]}_{user_ids[1]}'
        else:  # Group chat
            self.room_group_name = f'chat_group_{self.chat_id}'
        
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
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'message')
        
        if message_type == 'message':
            message = text_data_json['message']
            
            # Save message to database
            if self.chat_type == 'direct':
                receiver = await self.get_user(self.chat_id)
                message_obj = await self.save_direct_message(receiver, message)
                
                # Create notification
                await self.create_message_notification(receiver, message_obj)
            else:  # Group chat
                group = await self.get_group(self.chat_id)
                message_obj = await self.save_group_message(group, message)
                
                # Create notifications for all group members except sender
                await self.create_group_message_notifications(group, message_obj)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_id': self.user.id,
                    'sender_username': self.user.username,
                    'timestamp': message_obj.timestamp.isoformat()
                }
            )
        elif message_type == 'typing':
            # Send typing status to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_status',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'is_typing': text_data_json['is_typing']
                }
            )
    
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'attachment_url': event.get('attachment_url'),
            'timestamp': event['timestamp']
        }))
    
    async def typing_status(self, event):
        # Send typing status to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing']
        }))
    
    @database_sync_to_async
    def get_user(self, user_id):
        return User.objects.get(id=user_id)
    
    @database_sync_to_async
    def get_group(self, group_id):
        return ChatGroup.objects.get(id=group_id)
    
    @database_sync_to_async
    def save_direct_message(self, receiver, content):
        message = Message.objects.create(
            sender=self.user,
            receiver=receiver,
            content=content
        )
        return message
    
    @database_sync_to_async
    def save_group_message(self, group, content):
        message = Message.objects.create(
            sender=self.user,
            group=group,
            content=content
        )
        return message
    
    @database_sync_to_async
    def create_message_notification(self, receiver, message):
        Notification.objects.create(
            user=receiver,
            notification_type='message',
            sender=self.user,
            message=f"New message from {self.user.username}",
            related_message=message
        )
    
    @database_sync_to_async
    def create_group_message_notifications(self, group, message):
        for member in group.members.all().exclude(id=self.user.id):
            Notification.objects.create(
                user=member,
                notification_type='message',
                sender=self.user,
                message=f"New message in {group.name} from {self.user.username}",
                related_message=message,
                related_group=group
            )

