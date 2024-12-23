from django.db import models

# Create your models here.
class File(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='uploads/')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
class Pelicula(models.Model):
    title = models.CharField(max_length=200)
    descripcion = models.CharField(max_length=200, null=True, blank=True)