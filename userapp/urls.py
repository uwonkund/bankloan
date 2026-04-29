# from rest_framework_simplejwt.views import (
    
#     TokenRefreshView,
# )
# from django.urls import path
# from userapp.views import LoginMixin 
# urlpatterns =[
#     path('login/',LoginMixin.as_view(),name ='login'),
#     path('token/refresh/',TokenRefreshView.as_view(),name ='token_refresh')
# ]
from django.urls import path,include
from userapp.views import UserViewSet,LoginMixin
from rest_framework.routers import DefaultRouter

router=DefaultRouter()
router.register(r"users",UserViewSet,basename="user")
urlpatterns = [
    path("",include(router.urls)),
    path('login/', LoginMixin.as_view(), name='login'),
  
]