from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from ansible_base.lib.abstract_models import ImmutableCommonModel


class Entry(ImmutableCommonModel):
    """
    An activity stream entry.

    This is keyed on a generic object_id and content_type, which allows for
    a wide variety of objects to be used in the activity stream.
    """

    class Meta:
        verbose_name_plural = _('Entries')

    #: Describes the kind of activity stream entry being recorded
    #:
    #: create
    #:   The object is being stored for the first time (uses ``post_save`` signal)
    #: update
    #:   The object already existed and is being updated (uses ``pre_save`` signal)
    #: delete
    #:   The object is being deleted (uses ``pre_delete`` signal)
    #: associate
    #:   The object is being associated with another object (uses ``m2m_changed`` signal)
    #: disassociate
    #:   The object is being disassociated from another object (uses ``m2m_changed`` signal)
    OPERATION_CHOICES = [
        ('create', _('Entity created')),
        ('update', _("Entity updated")),
        ('delete', _("Entity deleted")),
        ('associate', _("Entity was associated with another entity")),
        ('disassociate', _("Entity was disassociated with another entity")),
    ]

    #: The type/model of the object being recorded
    content_type = models.ForeignKey(ContentType, on_delete=models.DO_NOTHING)

    #: The primary key of the object being recorded
    object_id = models.TextField(null=True, blank=True)

    #: The object being recorded (a generic foreign key)
    content_object = GenericForeignKey('content_type', 'object_id')

    #: The operation being performed on the object (see ``OPERATION_CHOICES``)
    operation = models.CharField(max_length=12, choices=OPERATION_CHOICES)

    #: A JSON dictionary of the changes made to the object
    #:
    #: The dictionary has three keys:
    #:
    #: added_fields
    #:   A dictionary of fields that were added. This will usually only be used when the object is created.
    #:   Internally, it is as if the object is being compared to a model with no fields.
    #: removed_fields
    #:   A dictionary of fields that were removed. This will usually only be used when the object is deleted.
    #:   Internally, it is as if the object is being compared to a model with no fields.
    #: changed_fields
    #:   A dictionary of fields that were changed. The format is ``{field_name: [old_value, new_value]}``.
    #:
    #: The values of all fields are stored as strings so that filtering and searching can be done on them.
    #: At serialization time, these strings are converted back to the correct type based on the model field
    #: from which they came.
    changes = models.JSONField(null=True, blank=True)

    #: The type/model of the related object, if the entry is documenting a many-to-many relationship
    related_content_type = models.ForeignKey(ContentType, on_delete=models.DO_NOTHING, null=True, blank=True, related_name='related_content_type')

    #: The primary key of the related object, if the entry is documenting a many-to-many relationship
    related_object_id = models.TextField(null=True, blank=True)

    #: The related object, if the entry is documenting a many-to-many relationship
    related_content_object = GenericForeignKey('related_content_type', 'related_object_id')

    #: The name of the field on the related object that is being associated or disassociated
    related_field_name = models.CharField(max_length=64, null=True, blank=True)

    def __str__(self):
        return f'[{self.created}] {self.get_operation_display()} by {self.created_by}: {self.content_type} {self.object_id}'


class AuditableModel(models.Model):
    """
    A mixin class that provides integration to the activity stream from any
    model. A model should simply inherit from this class to have its
    create/update/delete events sent to the activity stream.
    """

    class Meta:
        abstract = True

    #: Adding field names to this list will exclude them from the activity stream changes dictionaries
    activity_stream_excluded_field_names = []

    #: Adding field names to this list will limit the activity stream changes dictionaries to only include these fields
    activity_stream_limit_field_names = []

    @property
    def activity_stream_entries(self):
        """
        A helper property that returns the activity stream entries for this object.
        """
        return Entry.objects.filter(content_type=ContentType.objects.get_for_model(self), object_id=self.pk).order_by('created')
