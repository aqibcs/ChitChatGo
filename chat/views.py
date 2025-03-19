from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from .forms import (UserRegistrationForm, UserLoginForm, ProfileUpdateForm,
                    UserUpdateForm, ChatGroupForm, MessageForm)
from .models import (Profile, FriendRequest, Friendship, ChatGroup, Message, Notification, User)


# Authentication Views
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create profile for the user
            Profile.objects.create(user=user)
            messages.success(
                request,
                f'Account created for {user.username}! You can now log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'chat/register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Update online status
                profile = Profile.objects.get(user=user)
                profile.is_online = True
                profile.save()
                messages.success(request, f'Welcome back, {username}!')
                return redirect('chat_home')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    return render(request, 'chat/login.html', {'form': form})


@login_required
def user_logout(request):
    # Update online status
    profile = Profile.objects.get(user=request.user)
    profile.is_online = False
    profile.last_seen = timezone.now()
    profile.save()
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


# Profile Views
@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST,
                                   request.FILES,
                                   instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {'u_form': u_form, 'p_form': p_form}
    return render(request, 'chat/profile.html', context)


# Friend Management Views
@login_required
def friend_list(request):
    # Get all friendships where the current user is involved
    friendships = Friendship.objects.filter(
        Q(user1=request.user) | Q(user2=request.user))

    # Extract the friends from the friendships
    friends = []
    for friendship in friendships:
        if friendship.user1 == request.user:
            friends.append(friendship.user2)
        else:
            friends.append(friendship.user1)

    # Get pending friend requests
    pending_requests = FriendRequest.objects.filter(receiver=request.user,
                                                    status='pending')

    context = {'friends': friends, 'pending_requests': pending_requests}
    return render(request, 'chat/friend_list.html', context)


@login_required
def send_friend_request(request, user_id):
    receiver = get_object_or_404(User, id=user_id)

    # Check if a request already exists
    if FriendRequest.objects.filter(sender=request.user,
                                    receiver=receiver).exists():
        messages.warning(request, 'Friend request already sent.')
        return redirect('user_search')

    # Check if they are already friends
    if Friendship.objects.filter((Q(user1=request.user) & Q(user2=receiver))
                                 | (Q(user1=receiver)
                                    & Q(user2=request.user))).exists():
        messages.warning(request, 'You are already friends with this user.')
        return redirect('user_search')

    # Create friend request
    friend_request = FriendRequest.objects.create(sender=request.user,
                                                  receiver=receiver,
                                                  status='pending')

    # Create notification
    Notification.objects.create(
        user=receiver,
        notification_type='friend_request',
        sender=request.user,
        message=f"{request.user.username} sent you a friend request.",
        related_friend_request=friend_request)

    messages.success(request, f'Friend request sent to {receiver.username}.')
    return redirect('user_search')


@login_required
def accept_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest,
                                       id=request_id,
                                       receiver=request.user)

    # Update request status
    friend_request.status = 'accepted'
    friend_request.save()

    # Create friendship
    Friendship.objects.create(user1=request.user, user2=friend_request.sender)

    # Create notification
    Notification.objects.create(
        user=friend_request.sender,
        notification_type='friend_accept',
        sender=request.user,
        message=f"{request.user.username} accepted your friend request.",
        related_friend_request=friend_request)

    messages.success(
        request, f'You are now friends with {friend_request.sender.username}.')
    return redirect('friend_list')


@login_required
def reject_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest,
                                       id=request_id,
                                       receiver=request.user)

    # Update request status
    friend_request.status = 'rejected'
    friend_request.save()

    messages.success(
        request,
        f'Friend request from {friend_request.sender.username} rejected.')
    return redirect('friend_list')


@login_required
def remove_friend(request, user_id):
    friend = get_object_or_404(User, id=user_id)

    # Find and delete the friendship
    friendship = Friendship.objects.filter(
        (Q(user1=request.user) & Q(user2=friend))
        | (Q(user1=friend) & Q(user2=request.user))).first()

    if friendship:
        friendship.delete()
        messages.success(
            request, f'{friend.username} has been removed from your friends.')
    else:
        messages.error(request, 'Friendship not found.')

    return redirect('friend_list')


@login_required
def user_search(request):
    query = request.GET.get('q', '')
    users = []

    if query:
        # Search for users by username or email
        users = User.objects.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)).exclude(id=request.user.id)

        # Get existing friend requests and friendships
        sent_requests = FriendRequest.objects.filter(
            sender=request.user).values_list('receiver_id', flat=True)
        received_requests = FriendRequest.objects.filter(
            receiver=request.user).values_list('sender_id', flat=True)

        friendships = Friendship.objects.filter(
            Q(user1=request.user) | Q(user2=request.user))

        friends = []
        for friendship in friendships:
            if friendship.user1 == request.user:
                friends.append(friendship.user2.id)
            else:
                friends.append(friendship.user1.id)

        # Add status to each user
        for user in users:
            if user.id in friends:
                user.status = 'friend'
            elif user.id in sent_requests:
                user.status = 'request_sent'
            elif user.id in received_requests:
                user.status = 'request_received'
            else:
                user.status = 'not_friend'

    context = {'users': users, 'query': query}
    return render(request, 'chat/user_search.html', context)


# Chat Views
@login_required
def chat_home(request):
    # Get all friends
    friendships = Friendship.objects.filter(
        Q(user1=request.user) | Q(user2=request.user))

    friends = []
    for friendship in friendships:
        if friendship.user1 == request.user:
            friends.append(friendship.user2)
        else:
            friends.append(friendship.user1)

    # Get all groups the user is a member of
    groups = ChatGroup.objects.filter(members=request.user)

    # Get unread notifications count
    unread_count = Notification.objects.filter(user=request.user,
                                               is_read=False).count()

    context = {
        'friends': friends,
        'groups': groups,
        'unread_count': unread_count
    }
    return render(request, 'chat/chat_home.html', context)


@login_required
def direct_chat(request, user_id):
    friend = get_object_or_404(User, id=user_id)

    # Check if they are friends
    if not Friendship.objects.filter((Q(user1=request.user) & Q(user2=friend))
                                     | (Q(user1=friend)
                                        & Q(user2=request.user))).exists():
        messages.error(request, 'You can only chat with your friends.')
        return redirect('chat_home')

    # Get chat history
    messages_list = Message.objects.filter(
        (Q(sender=request.user) & Q(receiver=friend))
        | (Q(sender=friend) & Q(receiver=request.user))).order_by('timestamp')

    # Mark messages as read
    unread_messages = messages_list.filter(sender=friend,
                                           receiver=request.user, is_read=False)
    for msg in unread_messages:
        msg.is_read = True
        msg.save()

    # Handle new message
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.receiver = friend
            message.save()

            # Create notification
            Notification.objects.create(
                user=friend,
                notification_type='message',
                sender=request.user,
                message=f"New message from {request.user.username}",
                related_message=message)

            # If this is an AJAX request (for file uploads)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response_data = {
                    'status': 'success',
                    'message_id': message.id,
                }

                if message.attachment:
                    response_data['attachment_url'] = message.attachment.url

                return JsonResponse(response_data)

            return redirect('direct_chat', user_id=user_id)
    else:
        form = MessageForm()

    context = {'friend': friend, 'messages': messages_list, 'form': form}
    return render(request, 'chat/direct_chat.html', context)


@login_required
def group_chat(request, group_id):
    group = get_object_or_404(ChatGroup, id=group_id)

    # Check if user is a member of the group
    if request.user not in group.members.all():
        messages.error(request, 'You are not a member of this group.')
        return redirect('chat_home')

    # Get chat history
    messages_list = Message.objects.filter(group=group).order_by('timestamp')

    # Handle new message
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.group = group
            message.save()

            # Create notifications for all group members except sender
            for member in group.members.all().exclude(id=request.user.id):
                Notification.objects.create(
                    user=member,
                    notification_type='message',
                    sender=request.user,
                    message=
                    f"New message in {group.name} from {request.user.username}",
                    related_message=message,
                    related_group=group)

            # If this is an AJAX request (for file uploads)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response_data = {
                    'status': 'success',
                    'message_id': message.id,
                }

                if message.attachment:
                    response_data['attachment_url'] = message.attachment.url

                return JsonResponse(response_data)

            return redirect('group_chat', group_id=group_id)
    else:
        form = MessageForm()

    context = {
        'group': group,
        'messages': messages_list,
        'form': form,
        'members': group.members.all()
    }
    return render(request, 'chat/group_chat.html', context)


@login_required
def create_group(request):
    if request.method == 'POST':
        form = ChatGroupForm(request.POST, request.FILES)
        if form.is_valid():
            group = form.save(commit=False)
            group.creator = request.user
            group.save()

            # Add creator as a member
            group.members.add(request.user)

            # Add selected friends as members
            friend_ids = request.POST.getlist('friends')
            for friend_id in friend_ids:
                try:
                    friend = User.objects.get(id=friend_id)
                    group.members.add(friend)

                    # Create notification for each added member
                    Notification.objects.create(
                        user=friend,
                        notification_type='group_invite',
                        sender=request.user,
                        message=
                        f"{request.user.username} added you to the group {group.name}",
                        related_group=group)
                except User.DoesNotExist:
                    pass

            messages.success(request, f'Group "{group.name}" created successfully.')
            return redirect('group_chat', group_id=group.id)
    else:
        form = ChatGroupForm()

    # Get all friends to add to the group
    friendships = Friendship.objects.filter(
        Q(user1=request.user) | Q(user2=request.user))

    friends = []
    for friendship in friendships:
        if friendship.user1 == request.user:
            friends.append(friendship.user2)
        else:
            friends.append(friendship.user1)

    context = {'form': form, 'friends': friends}
    return render(request, 'chat/create_group.html', context)


@login_required
def manage_group(request, group_id):
    group = get_object_or_404(ChatGroup, id=group_id)

    # Check if user is the creator of the group
    if group.creator != request.user:
        messages.error(request, 'Only the group creator can manage the group.')
        return redirect('group_chat', group_id=group_id)

    if request.method == 'POST':
        form = ChatGroupForm(request.POST, request.FILES, instance=group)
        if form.is_valid():
            form.save()

            # Update members
            group.members.clear()
            group.members.add(request.user)  # Always keep the creator

            friend_ids = request.POST.getlist('friends')
            for friend_id in friend_ids:
                try:
                    friend = User.objects.get(id=friend_id)
                    group.members.add(friend)
                except User.DoesNotExist:
                    pass

            messages.success(request,
                             f'Group "{group.name}" updated successfully.')
            return redirect('group_chat', group_id=group_id)
    else:
        form = ChatGroupForm(instance=group)

    # Get all friends
    friendships = Friendship.objects.filter(
        Q(user1=request.user) | Q(user2=request.user))

    friends = []
    for friendship in friendships:
        if friendship.user1 == request.user:
            friends.append(friendship.user2)
        else:
            friends.append(friendship.user1)

    # Get current members
    current_members = group.members.all().exclude(id=request.user.id)

    context = {
        'form': form,
        'group': group,
        'friends': friends,
        'current_members': current_members
    }
    return render(request, 'chat/manage_group.html', context)


@login_required
def leave_group(request, group_id):
    group = get_object_or_404(ChatGroup, id=group_id)

    # Check if user is a member of the group
    if request.user not in group.members.all():
        messages.error(request, 'You are not a member of this group.')
        return redirect('chat_home')

    # Check if user is the creator
    if group.creator == request.user:
        messages.error(
            request,
            'As the creator, you cannot leave the group. You can delete it instead.'
        )
        return redirect('group_chat', group_id=group_id)

    # Remove user from group
    group.members.remove(request.user)
    messages.success(request, f'You have left the group "{group.name}".')
    return redirect('chat_home')


@login_required
def delete_group(request, group_id):
    group = get_object_or_404(ChatGroup, id=group_id)

    # Check if user is the creator of the group
    if group.creator != request.user:
        messages.error(request, 'Only the group creator can delete the group.')
        return redirect('group_chat', group_id=group_id)

    group_name = group.name
    group.delete()
    messages.success(request, f'Group "{group_name}" has been deleted.')
    return redirect('chat_home')


# Notification Views
@login_required
def notifications(request):
    notifications_list = Notification.objects.filter(
        user=request.user).order_by('-created_at')

    # Mark all as read
    if request.method == 'POST' and 'mark_all_read' in request.POST:
        notifications_list.update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
        return redirect('notifications')

    context = {'notifications': notifications_list}
    return render(request, 'chat/notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification,
                                     id=notification_id,
                                     user=request.user)
    notification.is_read = True
    notification.save()

    # Redirect based on notification type
    if notification.notification_type == 'message':
        if notification.related_group:
            return redirect('group_chat',
                            group_id=notification.related_group.id)
        elif notification.related_message and notification.related_message.receiver:
            return redirect('direct_chat',
                            user_id=notification.related_message.sender.id)
    elif notification.notification_type == 'friend_request':
        return redirect('friend_list')
    elif notification.notification_type == 'group_invite':
        return redirect('group_chat', group_id=notification.related_group.id)

    return redirect('notifications')


# AJAX Views for Real-time Updates
@login_required
def get_unread_count(request):
    unread_count = Notification.objects.filter(user=request.user,
                                               is_read=False).count()
    return JsonResponse({'unread_count': unread_count})


@login_required
def get_online_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = Profile.objects.get(user=user)

    data = {
        'is_online': profile.is_online,
        'last_seen':
        profile.last_seen.isoformat() if profile.last_seen else None
    }
    return JsonResponse(data)
