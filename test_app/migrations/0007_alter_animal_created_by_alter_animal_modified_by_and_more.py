# Generated by Django 4.2.8 on 2024-04-05 13:06

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('test_app', '0006_team_admins_team_users'),
    ]

    operations = [
        migrations.AlterField(
            model_name='animal',
            name='created_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who created this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='animal',
            name='modified_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who last modified this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='city',
            name='created_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who created this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='city',
            name='modified_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who last modified this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='encryptionmodel',
            name='created_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who created this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='encryptionmodel',
            name='modified_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who last modified this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='immutablelogentry',
            name='created_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who created this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='multiplefieldsmodel',
            name='created_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who created this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='multiplefieldsmodel',
            name='modified_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who last modified this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='organization',
            name='created_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who created this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='organization',
            name='modified_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who last modified this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='original1',
            name='created_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who created this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='original1',
            name='modified_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who last modified this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='original2',
            name='created_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who created this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='original2',
            name='modified_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who last modified this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='relatedfieldstestmodel',
            name='created_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who created this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='relatedfieldstestmodel',
            name='modified_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who last modified this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='team',
            name='created_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who created this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='team',
            name='modified_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who last modified this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='user',
            name='created_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who created this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='user',
            name='modified_by',
            field=models.ForeignKey(default=None, editable=False, help_text='The user who last modified this resource', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified+', to=settings.AUTH_USER_MODEL),
        ),
    ]
