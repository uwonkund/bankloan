from django.shortcuts import render
from rest_framework_simplejwt.views import TokenViewBase 
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.exceptions import TokenError ,InvalidToken
from userapp.serializers import CustomTokenObtainPairSerializer
from django.contrib.auth.models import User

class LoginMixin(APIView):
    '''
        User login with either Jwt token or Two Factor auth
    '''
    custom_serializer = CustomTokenObtainPairSerializer
    queryset = User.objects.all()
    permission_classes =[AllowAny]

    def post(self, request, *args, **kwargs):
        '''
        User login with Jwt token
        params : username , password
        return : Jwt token
        '''
        serializer = self.custom_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

# Create your views here.
