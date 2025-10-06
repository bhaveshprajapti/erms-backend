from rest_framework import viewsets
from .models import Client, ClientRole, Quotation
from .serializers import ClientSerializer, ClientRoleSerializer, QuotationSerializer

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class ClientRoleViewSet(viewsets.ModelViewSet):
    queryset = ClientRole.objects.all()
    serializer_class = ClientRoleSerializer

class QuotationViewSet(viewsets.ModelViewSet):
    queryset = Quotation.objects.all()
    serializer_class = QuotationSerializer

