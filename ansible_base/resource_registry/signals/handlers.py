import logging
from functools import lru_cache

from crum import get_current_user
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from ansible_base.resource_registry.models import Resource, init_resource_from_object
from ansible_base.resource_registry.registry import get_registry
from ansible_base.resource_registry.rest_client import ResourceRequestBody, get_resource_server_client

logger = logging.getLogger('ansible_base.resource_registry.signals.handlers')


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


def sync_to_resource_server(instance, action):
    """
    Use the resource server API to sync the resource across.
    """
    try:
        if not getattr(instance, 'resource', None) or not instance.resource.ansible_id:
            # We can't sync if we don't have a resource and an ansible_id.
            return
    except Resource.DoesNotExist:
        # The getattr() will raise a Resource.DoesNotExist if the resource doesn't exist.
        return

    user = get_current_user()
    if not user:
        # TODO: What should we do if there's no user (e.g. CLI app?)
        # Sync as _system?
        return

    try:
        user_ansible_id = user.resource.ansible_id
    except AttributeError:
        # TODO: What should we do if we're e.g. AnonymousUser and don't have an ansible_id?
        return

    client = get_resource_server_client(
        settings.RESOURCE_SERVICE_PATH,
        jwt_user_id=user_ansible_id,
        raise_if_bad_request=True,
    )

    ansible_id = instance.resource.ansible_id

    resource_type = instance.resource.content_type.resource_type
    data = resource_type.serializer_class(instance).data
    body = ResourceRequestBody(
        resource_type=resource_type.name,
        ansible_id=ansible_id,
        service_id=instance.resource.service_id,
        resource_data=data,
    )

    try:
        if action == "create":
            client.create_resource(body)
        elif action == "update":
            client.update_resource(ansible_id, body)
        elif action == "delete":
            client.delete_resource(ansible_id)
    except Exception as e:
        logger.exception(f"Failed to sync {action} of resource {ansible_id} to resource server: {e}")
        raise ValidationError(_("Failed to sync resource to resource server")) from e
