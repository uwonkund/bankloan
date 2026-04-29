from django.contrib.auth.models import User
from rest_framework import serializers 
from rest_framework_simplejwt.serializers import  TokenObtainPairSerializer
import datetime

class UserSerializer (serializers.Serializer):
    username =serializers.CharField()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer) :
    @classmethod 
    def get_token(cls,user):

        User.objects.filter(id=user.id).update(
            last_login=datetime.datetime.now()
        ) 
        token=super().get_token(user)
        token["full_name"] =f"{user.first_name}{user.last_name}"
        token ["email"] =user.email
        return token 