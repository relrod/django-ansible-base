import logging
import sys
from functools import lru_cache

from crum import get_current_user
from django.conf import settings
from django.db import transaction
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


def _should_reverse_sync():
    enabled = not getattr(settings, 'DISABLE_RESOURCE_SERVER_SYNC', False)
    for setting in ('RESOURCE_SERVER', 'RESOURCE_SERVICE_PATH'):
        if not getattr(settings, setting, False):
            enabled = False
            break
    return enabled


def _ensure_transaction(instance):
    """
    Ensure that the save happens within a transaction, so that when a save
    fails, we don't end up in an inconsistant state by writing to the resource
    server from a service. We want to avoid having updates sent when the update
    didn't actually take place locally.
    """
    if not _should_reverse_sync():
        return
    instance._transaction = transaction.atomic()
    instance._transaction.__enter__()


# pre_save
def sync_to_resource_server_pre_save(sender, instance, raw, using, update_fields, **kwargs):
    """
    Lightweight wrapper over _ensure_transaction() for pre_save (create/update)
    """
    _ensure_transaction(instance)


# pre_delete
def sync_to_resource_server_pre_delete(sender, instance, using, origin, **kwargs):
    """
    Lightweight wrapper over _ensure_transaction() for pre_delete
    """
    _ensure_transaction(instance)


# post_save
def sync_to_resource_server_post_save(sender, instance, created, raw, using, update_fields, **kwargs):
    """
    Sync the resource to the resource server.
    """
    action = 'create' if created else 'update'
    sync_to_resource_server(action, instance)


# post_delete
def sync_to_resource_server_post_delete(sender, instance, using, origin, **kwargs):
    """
    Sync the resource to the resource server.
    """
    sync_to_resource_server('delete', instance)


def sync_to_resource_server(action, instance):
    """
    Use the resource server API to sync the resource across.
    """

    if not _should_reverse_sync():
        return

    exc = False
    try:

        # /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\
        # Do NOT put any early return logic outside of the try/finally, because
        # we need to reach the end of the function to commit/rollback the transaction.
        # /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\

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

        if action in ('create', 'update'):
            resource_type = instance.resource.content_type.resource_type
            data = resource_type.serializer_class(instance).data
            body = ResourceRequestBody(
                resource_type=resource_type.name,
                ansible_id=ansible_id,
                service_id=instance.resource.service_id,
                resource_data=data,
            )

            if action == 'create':
                client.create_resource(body)
            else:
                client.update_resource(ansible_id, body)
        elif action == 'delete':
            client.delete_resource(ansible_id)
    except Exception as e:
        logger.exception("Failed to sync resource to resource server")

        if hasattr(instance, '_transaction'):
            exc = True
            if not instance._transaction.__exit__(*sys.exc_info()):
                msg = _("Failed to sync resource to resource server")
                raise ValidationError(msg) from e
    finally:
        if hasattr(instance, '_transaction'):
            if not exc:
                instance._transaction.__exit__(None, None, None)
