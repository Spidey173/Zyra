from django.urls import path
from . import views

urlpatterns = [
    # Authentication & Landing
    path('', views.landing, name='landing'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Feeds & Exploration
    path('home/', views.home, name='home'),
    path('explore/', views.explore_view, name='explore'),
    path('reels/', views.reels_view, name='reels'),
    path('activity/', views.notifications_view, name='notifications'),

    # Posts & Interactions
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('post/like/<int:post_id>/', views.like_post, name='like_post'),
    path('post/comment/<int:post_id>/', views.comment_post, name='comment_post'),
    path('comment/delete/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    path('post/bookmark/<int:post_id>/', views.toggle_bookmark, name='toggle_bookmark'),
    path('post/delete/<int:post_id>/', views.delete_post, name='delete_post'),

    # Stories
    path('story/create/', views.create_story_view, name='create_story'),
    path('story/delete/<int:story_id>/', views.delete_story_view, name='delete_story'),

    # User Profiles & Follow Graph
    path('user/<str:username>/', views.user_profile, name='user_profile'),
    path('user/<str:username>/follow/', views.follow_user, name='follow_user'),
    path('profile/<str:username>/followers/', views.followers_list, name='followers_list'),
    path('profile/<str:username>/following/', views.following_list, name='following_list'),

    # Direct Messaging (Instagram Direct)
    path('direct/', views.direct_inbox, name='direct_inbox'),
    path('direct/t/<str:username>/', views.direct_inbox, name='direct_chat'),
    path('direct/api/send/<int:conversation_id>/', views.send_message_api, name='send_message_api'),
    path('direct/api/messages/<int:conversation_id>/', views.get_messages_api, name='get_messages_api'),
    path('direct/api/read/<int:conversation_id>/', views.mark_as_read_api, name='mark_as_read_api'),
    path('direct/api/search-users/', views.search_users_for_dm, name='search_users_for_dm'),
    path('direct/api/share-post/', views.share_post_to_dm, name='share_post_to_dm'),
    path('direct/api/unsend/<int:message_id>/', views.unsend_message_api, name='unsend_message_api'),
    path('direct/api/edit/<int:message_id>/', views.edit_message_api, name='edit_message_api'),
    path('direct/api/react/<int:message_id>/', views.react_message_api, name='react_message_api'),
    path('direct/api/theme/<int:conversation_id>/', views.set_conversation_theme_api, name='set_conversation_theme_api'),
    path('direct/api/hide/<int:conversation_id>/', views.hide_conversation_api, name='hide_conversation_api'),
]
