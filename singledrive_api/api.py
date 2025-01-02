from rest_framework import generics
from .models import File, Pelicula
from .serializers import FileSerializer, PeliculaSerializer

# Vistas para CRUD de archivos
class FileListCreateView(generics.ListCreateAPIView):
    serializer_class = FileSerializer
    queryset = File.objects.all()

class FileRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = File.objects.all()
    serializer_class = FileSerializer


class PeliculaListCreateView(generics.ListCreateAPIView):
    serializer_class = PeliculaSerializer
    queryset = Pelicula.objects.all()  
   

class PeliculaRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Pelicula.objects.all()
    serializer_class = PeliculaSerializer


