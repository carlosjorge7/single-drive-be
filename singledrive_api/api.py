from rest_framework import generics
from .models import File
from .serializers import FileSerializer

class FileListCreateView(generics.ListCreateAPIView):
    serializer_class = FileSerializer
    queryset = File.objects.all()

class FileRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = File.objects.all()
    serializer_class = FileSerializer
   

