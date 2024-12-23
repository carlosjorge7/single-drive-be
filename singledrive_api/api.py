from rest_framework import generics
from .models import File, Pelicula
from .serializers import FileSerializer, PeliculaSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
import openai
import os

# Vistas para CRUD de archivos
class FileListCreateView(generics.ListCreateAPIView):
    serializer_class = FileSerializer
    queryset = File.objects.all()

class FileRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = File.objects.all()
    serializer_class = FileSerializer

# Vista para generar recetas con IA
class RecipeGeneratorView(APIView):
    def post(self, request):
        ingredients = request.data.get('ingredients', [])
        if not ingredients:
            return Response({'error': 'No ingredients provided'}, status=400)
        
        # Configura la API Key de OpenAI
        openai.api_key = os.getenv("OPENAI_API_KEY")

        # Genera una receta con GPT-3.5-turbo
        prompt = f"Genera una recetas con los siguientes ingredientes: {', '.join(ingredients)}."
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        
        recipe = response['choices'][0]['message']['content'].strip()
        return Response({'recipe': recipe})
    

class PeliculaListCreateView(generics.ListCreateAPIView):
    serializer_class = PeliculaSerializer
    queryset = Pelicula.objects.all()  
   

class PeliculaRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Pelicula.objects.all()
    serializer_class = PeliculaSerializer


