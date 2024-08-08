from functools import lru_cache

from ansible_base.resource_registry.models import Resource, init_resource_from_object
from ansible_base.resource_registry.registry import get_registry


@lru_cache(maxsize=1)
def get_resource_models():
    resource_models = set()
    registry = get_registry()
    if registry:
        for k, resource in registry.get_resources().items():
            resource_models.add(resource.model)

    return resource_models


def remove_resource(sender, instance, **kwargs):
    try:
        resource = Resource.get_resource_for_object(instance)
        resource.delete()
    except Resource.DoesNotExist:
        return


def update_resource(sender, instance, created, **kwargs):
    try:
        resource = Resource.get_resource_for_object(instance)
        resource.update_from_content_object()
    except Resource.DoesNotExist:
        resource = init_resource_from_object(instance)
        resource.save()


def decide_to_sync_update(sender, instance, raw, using, update_fields, **kwargs):
    """
    A pre_save hook that decides whether or not to reverse-sync the instance
    based on which fields have changed.
    """

    if instance._state.adding:
        # We only concern ourselves with updates
        return

    try:
        if not getattr(instance, 'resource', None) or not instance.resource.ansible_id:
            # We can't sync here, but we want to log that, so let sync_to_resource_server() discard it.
            return
    except Resource.DoesNotExist:
        # The getattr() will raise a Resource.DoesNotExist if the resource doesn't exist.
        return

    fields_that_sync = instance.resource.content_type.resource_type.serializer_class().get_fields().keys()

    if update_fields is None:
        # If we're not given a useful update_fields, manually calculate the changed fields
        # at the cost of an extra query
        existing_instance = sender.objects.get(pk=instance.pk)
        changed_fields = set()
        for field in fields_that_sync:
            if getattr(existing_instance, field) != getattr(instance, field):
                changed_fields.add(field)
    else:
        # If we're given update_fields, we can just check those
        changed_fields = set(update_fields)

    if not changed_fields.intersection(fields_that_sync):
        instance._skip_reverse_resource_sync = True
