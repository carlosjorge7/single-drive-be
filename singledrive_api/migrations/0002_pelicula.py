# Generated by Django 5.1.3 on 2024-12-23 14:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('singledrive_api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pelicula',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('descripcion', models.CharField(blank=True, max_length=200, null=True)),
            ],
        ),
    ]