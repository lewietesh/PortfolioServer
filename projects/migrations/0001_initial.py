# Generated by Django 5.2.4 on 2025-07-25 11:12

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, editable=False, max_length=36, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('category', models.CharField(blank=True, max_length=100)),
                ('domain', models.CharField(blank=True, help_text='Business domain or industry', max_length=100)),
                ('image_url', models.TextField(blank=True, help_text='Main project screenshot or banner')),
                ('description', models.TextField()),
                ('content', models.TextField(blank=True, help_text='Detailed project content and case study')),
                ('url', models.TextField(blank=True, help_text='Live project URL')),
                ('repository_url', models.TextField(blank=True, help_text='GitHub or code repository URL')),
                ('likes', models.IntegerField(default=0)),
                ('featured', models.BooleanField(default=False)),
                ('completion_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('ongoing', 'Ongoing'), ('completed', 'Completed'), ('maintenance', 'Maintenance')], default='ongoing', max_length=20)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(blank=True, limit_choices_to={'role': 'client'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='client_projects', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Project',
                'verbose_name_plural': 'Projects',
                'db_table': 'project',
                'ordering': ['-date_created'],
            },
        ),
        migrations.CreateModel(
            name='Technology',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('icon_url', models.TextField(blank=True)),
                ('category', models.CharField(blank=True, help_text='Category: frontend, backend, database, tool, etc.', max_length=50)),
            ],
            options={
                'verbose_name': 'Technology',
                'verbose_name_plural': 'Technologies',
                'db_table': 'technology',
                'ordering': ['category', 'name'],
                'indexes': [models.Index(fields=['name'], name='technology_name_ef7438_idx'), models.Index(fields=['category'], name='technology_categor_e82aba_idx')],
            },
        ),
        migrations.CreateModel(
            name='ProjectTechnology',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.project')),
                ('technology', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.technology')),
            ],
            options={
                'verbose_name': 'Project Technology',
                'verbose_name_plural': 'Project Technologies',
                'db_table': 'project_technology',
                'unique_together': {('project', 'technology')},
            },
        ),
        migrations.AddField(
            model_name='project',
            name='technologies',
            field=models.ManyToManyField(blank=True, related_name='projects', through='projects.ProjectTechnology', to='projects.technology'),
        ),
        migrations.CreateModel(
            name='ProjectComment',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, editable=False, max_length=36, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('message', models.TextField()),
                ('approved', models.BooleanField(default=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='projects.project')),
            ],
            options={
                'verbose_name': 'Project Comment',
                'verbose_name_plural': 'Project Comments',
                'db_table': 'project_comment',
                'ordering': ['-date_created'],
                'indexes': [models.Index(fields=['project'], name='project_com_project_c29a95_idx'), models.Index(fields=['approved'], name='project_com_approve_069ed4_idx')],
            },
        ),
        migrations.CreateModel(
            name='ProjectGalleryImage',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('image_url', models.TextField()),
                ('alt_text', models.CharField(blank=True, help_text='Alternative text for accessibility', max_length=255)),
                ('sort_order', models.IntegerField(default=0)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gallery_images', to='projects.project')),
            ],
            options={
                'verbose_name': 'Project Gallery Image',
                'verbose_name_plural': 'Project Gallery Images',
                'db_table': 'project_gallery_image',
                'ordering': ['project', 'sort_order'],
                'indexes': [models.Index(fields=['project'], name='project_gal_project_828c43_idx')],
            },
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['slug'], name='project_slug_99d028_idx'),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['status'], name='project_status_37437c_idx'),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['featured'], name='project_feature_2c6d4f_idx'),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['client'], name='project_client__3ae9f5_idx'),
        ),
    ]
