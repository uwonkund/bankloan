from django.urls import path, include
from rest_framework.routers import DefaultRouter
from loanapplication.views import LoanApplicationViewSet, LoanDocumentViewSet

router = DefaultRouter()
router.register(r'applications', LoanApplicationViewSet, basename='loanapplication')
router.register(r'documents', LoanDocumentViewSet, basename='loandocument')

urlpatterns = [
    path('', include(router.urls)),
]
