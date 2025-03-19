from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    
    # Friend Management URLs
    path('friends/', views.friend_list, name='friend_list'),
    path('friends/add/<int:user_id>/', views.send_friend_request, name='send_friend_request'),
    path('friends/accept/<int:request_id>/', views.accept_friend_request, name='accept_friend_request'),
    path('friends/reject/<int:request_id>/', views.reject_friend_request, name='reject_friend_request'),
    path('friends/remove/<int:user_id>/', views.remove_friend, name='remove_friend'),
    path('users/search/', views.user_search, name='user_search'),
    
    # Chat URLs
    path('', views.chat_home, name='chat_home'),
    path('chat/<int:user_id>/', views.direct_chat, name='direct_chat'),
    path('group/<int:group_id>/', views.group_chat, name='group_chat'),
    path('group/create/', views.create_group, name='create_group'),
    path('group/manage/<int:group_id>/', views.manage_group, name='manage_group'),
    path('group/leave/<int:group_id>/', views.leave_group, name='leave_group'),
    path('group/delete/<int:group_id>/', views.delete_group, name='delete_group'),
    
    # Notification URLs
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    
    # AJAX URLs
    path('ajax/unread-count/', views.get_unread_count, name='get_unread_count'),
    path('ajax/online-status/<int:user_id>/', views.get_online_status, name='get_online_status'),
]
