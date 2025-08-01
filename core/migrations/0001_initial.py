# Generated by Django 5.2.4 on 2025-07-25 11:12

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AboutSection',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('media_url', models.TextField(blank=True, help_text='URL for profile image or video')),
                ('socials_urls', models.JSONField(blank=True, help_text="JSON array of social media links: [{'name': 'twitter', 'url': '...'}]", null=True)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now)),
                ('date_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'About Section',
                'verbose_name_plural': 'About Sections',
                'db_table': 'about_section',
                'ordering': ['-date_created'],
            },
        ),
        migrations.CreateModel(
            name='HeroSection',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('heading', models.CharField(max_length=255)),
                ('subheading', models.CharField(blank=True, max_length=500)),
                ('cta_text', models.CharField(blank=True, help_text='Call-to-action button text', max_length=100)),
                ('cta_link', models.TextField(blank=True, help_text='Call-to-action button URL')),
                ('is_active', models.BooleanField(default=True, help_text='Only one hero section should be active at a time')),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now)),
                ('date_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Hero Section',
                'verbose_name_plural': 'Hero Sections',
                'db_table': 'hero_section',
                'ordering': ['-date_created'],
            },
        ),
    ]
