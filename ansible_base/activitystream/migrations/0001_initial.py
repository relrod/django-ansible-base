# Generated by Django 4.2.8 on 2024-02-14 15:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Entry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(default=None, editable=False, help_text='The date/time this resource was created')),
                ('modified_on', models.DateTimeField(default=None, editable=False, help_text='The date/time this resource was created')),
                ('object_id', models.TextField()),
                ('operation', models.CharField(choices=[('create', 'Entity Created'), ('update', 'Entity Updated'), ('delete', 'Entity Deleted'), ('associate', 'Entity Associated with another Entity'), ('disassociate', 'Entity was Disassociated with another Entity')], max_length=12)),
                ('changes', models.JSONField(blank=True, null=True)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('created_by', models.ForeignKey(default=None, editable=False, help_text='The user who created this resource', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='%(app_label)s_%(class)s_created+', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(default=None, editable=False, help_text='The user who last modified this resource', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='%(app_label)s_%(class)s_modified+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Entries',
            },
        ),
    ]
