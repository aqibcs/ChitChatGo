from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pics', default='profile_pics/default_user.png')
    bio = models.TextField(max_length=500, blank=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)

    def get_avatar_url(self):
        """Returns the user's profile picture or the default avatar."""
        if self.profile_picture:
            return self.profile_picture.url
        return 'profile_pics/default_user.png'

    def __str__(self):
        return f"{self.user.username}'s Profile"

class FriendRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    
    sender = models.ForeignKey(User, related_name='sent_requests', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_requests', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('sender', 'receiver')
    
    def __str__(self):
        return f"{self.sender.username} to {self.receiver.username} - {self.status}"

class Friendship(models.Model):
    user1 = models.ForeignKey(User, related_name='friendships1', on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name='friendships2', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user1', 'user2')
    
    def __str__(self):
        return f"{self.user1.username} and {self.user2.username}"

class ChatGroup(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(User, related_name='created_groups', on_delete=models.CASCADE)
    members = models.ManyToManyField(User, related_name='group_chats')
    created_at = models.DateTimeField(auto_now_add=True)
    group_picture = models.ImageField(upload_to='group_pics', default='group_pics/default_group.jpg')

    def get_group_avatar_url(self):
        """Returns the group picture or the default group avatar."""
        if self.group_picture and self.group_picture.url:
            return self.group_picture.url
        return 'group_pics/default_group.jpg'

    def __str__(self):
        return self.name


class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    # For direct messages
    receiver = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE, null=True, blank=True)
    # For group messages
    group = models.ForeignKey(ChatGroup, related_name='messages', on_delete=models.CASCADE, null=True, blank=True)
    # For file attachments
    attachment = models.FileField(upload_to='message_attachments', null=True, blank=True)
    
    def __str__(self):
        if self.group:
            return f"{self.sender.username} in {self.group.name}: {self.content[:20]}"
        else:
            return f"{self.sender.username} to {self.receiver.username}: {self.content[:20]}"

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('message', 'New Message'),
        ('friend_request', 'Friend Request'),
        ('friend_accept', 'Friend Request Accepted'),
        ('group_invite', 'Group Invitation'),
    )
    
    user = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    sender = models.ForeignKey(User, related_name='sent_notifications', on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Related objects
    related_message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True)
    related_friend_request = models.ForeignKey(FriendRequest, on_delete=models.CASCADE, null=True, blank=True)
    related_group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return f"{self.notification_type} for {self.user.username} from {self.sender.username}"
