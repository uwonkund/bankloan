from rest_framework_simplejwt.views import (
    
    TokenRefreshView,
)
from django.urls import path
from userapp.views import LoginMixin 
urlpatterns =[
    path('login/',LoginMixin.as_view(),name ='login'),
    path('token/refresh/',TokenRefreshView.as_view(),name ='token_refresh')
]