from django.contrib import admin
from .models import Profile, FriendRequest, Friendship, ChatGroup, Message, Notification

admin.site.register(Profile)
admin.site.register(FriendRequest)
admin.site.register(Friendship)
admin.site.register(ChatGroup)
admin.site.register(Message)
admin.site.register(Notification)
