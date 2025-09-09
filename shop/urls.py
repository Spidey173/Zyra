from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/remove/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.proceed_to_payment, name='proceed_to_payment'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('signup/', views.signup, name='signup'),

    # ─── your custom logout must come BEFORE the auth include ───
    path('accounts/logout/', views.custom_logout, name='logout'),

    # then include the rest of django.contrib.auth URLs
    path('accounts/', include('django.contrib.auth.urls')),
]
