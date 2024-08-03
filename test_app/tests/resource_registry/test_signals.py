from unittest import mock

import pytest
from crum import impersonate
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.exceptions import ValidationError

from ansible_base.resource_registry.signals import handlers
from test_app.models import EncryptionModel, Organization, Original1, Original2, Proxy1, Proxy2

handlers_path = 'ansible_base.resource_registry.signals.handlers'


@pytest.mark.django_db
def test_unregistered_model_triggers_no_signals():
    with mock.patch('ansible_base.resource_registry.models.resource.init_resource_from_object') as mck:
        obj = EncryptionModel.objects.create()
    mck.assert_not_called()

    with mock.patch('ansible_base.resource_registry.models.Resource.update_from_content_object') as mck:
        obj.a = 'foobar'
        obj.save()
    mck.assert_not_called()

    with mock.patch('ansible_base.resource_registry.models.Resource.delete') as mck:
        obj.delete()
    mck.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize('model', [Organization, Original1, Original2, Proxy1, Proxy2])
def test_registered_model_triggers_signals(model, system_user):
    with mock.patch('ansible_base.resource_registry.signals.handlers.init_resource_from_object', wraps=handlers.init_resource_from_object) as mck:
        obj = model.objects.create(name='foo')
    mck.assert_called_once_with(obj)

    with mock.patch('ansible_base.resource_registry.models.Resource.update_from_content_object') as mck:
        obj.description = 'foobar'
        obj.save()
    mck.assert_called_once_with()

    with mock.patch('ansible_base.resource_registry.models.Resource.delete') as mck:
        obj.delete()
    mck.assert_called_once_with()


@pytest.mark.django_db
@pytest.mark.parametrize('action', ['create', 'update', 'delete'])
def test_sync_to_resource_server_happy_path(settings, user, action):
    """
    We don't have a "real" resource server for test_app to sync against, so we
    mock the client and just check that the right methods are called and ensure
    that the whole thing happens in a transaction so that if the reverse sync
    fails, we don't commit the change locally.

    This test specifically tests the happy/green path for create/update/delete.
    It ensures a transaction is created, the resource server client is called
    with the right action, and the transaction is released at the end.

    Hot damn, this is a gnarly test.
    """
    settings.DISABLE_RESOURCE_SERVER_SYNC = False

    if action in ('delete', 'update'):
        # If we're updating or deleting, we need an existing object,
        # create it before we start patching and tracking queries
        org = Organization.objects.create(name='Hello')

    with mock.patch(f'{handlers_path}.get_resource_server_client') as get_resource_server_client:
        with impersonate(user):
            with CaptureQueriesContext(connection) as queries:
                if action == 'create':
                    org = Organization.objects.create(name='Hello')
                elif action == 'update':
                    org.name = 'World'
                    org.save()
                elif action == 'delete':
                    org.delete()

    # We call the client to make the actual request to the resource server
    client_method = getattr(get_resource_server_client.return_value, f'{action}_resource')
    client_method.assert_called_once()

    # The whole thing is wrapped in a transaction/savepoint
    if action in ('create', 'update'):
        assert queries.captured_queries[0]['sql'].startswith('SAVEPOINT'), queries.captured_queries[0]['sql']
    else:
        # For delete there are a bunch of selects before the savepoint
        # So find the savepoint and ensure it's the right one (right before the delete)
        for i, query in enumerate(queries.captured_queries):
            if query['sql'].startswith('SAVEPOINT'):
                break
        assert queries.captured_queries[i + 1]['sql'].startswith('DELETE'), queries.captured_queries[i + 1]['sql']

    assert queries.captured_queries[-1]['sql'].startswith('RELEASE SAVEPOINT'), queries.captured_queries[-1]['sql']


@pytest.mark.django_db
@pytest.mark.parametrize('anon', [AnonymousUser(), None])
def test_sync_to_resource_server_unauthenticated(settings, anon):
    """
    If we don't have a user (e.g. we are a CLI app) or somehow we are here but
    with an anonymous user, we should... (TODO: what should we do? Sync as _system?)
    """
    settings.DISABLE_RESOURCE_SERVER_SYNC = False

    with mock.patch(f'{handlers_path}.get_resource_server_client') as get_resource_server_client:
        with impersonate(anon):
            Organization.objects.create(name='Hello')

    # Currently we bail out before we even have a client
    get_resource_server_client.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize('nullify_resource', [pytest.param(True, id="resource is None"), pytest.param(False, id="resource is not None but does not exist")])
def test_sync_to_resource_server_no_resource(settings, user, nullify_resource):
    """
    Somehow we are trying to sync a model that doesn't have a resource associated
    with it. This should be a no-op.
    """
    settings.DISABLE_RESOURCE_SERVER_SYNC = False

    # Just mock this out so we don't create a resource on the object
    with mock.patch(f'{handlers_path}.init_resource_from_object'):
        org = Organization(name='Hello')
        if nullify_resource:
            org.resource = None
        org.save()

        with mock.patch(f'{handlers_path}.get_resource_server_client') as get_resource_server_client:
            with impersonate(user):
                org.name = 'World'
                org.save()

    # We bail out if we don't have a resource
    get_resource_server_client.assert_not_called()


@pytest.mark.django_db
def test_sync_to_resource_server_exception(settings, user):
    """
    We get an exception when trying to sync (e.g. the server gives us a 500, or
    we can't connect, etc.). We raise ValidationError and don't commit the change.
    """
    settings.DISABLE_RESOURCE_SERVER_SYNC = False

    with mock.patch(f'{handlers_path}.get_resource_server_client') as get_resource_server_client:
        get_resource_server_client.return_value.create_resource.side_effect = Exception('Boom!')
        with impersonate(user):
            with CaptureQueriesContext(connection) as queries:
                with pytest.raises(ValidationError, match="Failed to sync resource"):
                    org = Organization.objects.create(name='Hello')

    # The last two queries should be a rollback
    assert queries.captured_queries[-2]['sql'].startswith('ROLLBACK'), queries.captured_queries[-2]['sql']
    assert queries.captured_queries[-1]['sql'].startswith('RELEASE SAVEPOINT'), queries.captured_queries[-1]['sql']


@pytest.mark.parametrize(
    'new_settings,should_sync',
    [
        ({'DISABLE_RESOURCE_SERVER_SYNC': False, 'RESOURCE_SERVER': {}, 'RESOURCE_SERVICE_PATH': "/foo"}, False),
        ({'DISABLE_RESOURCE_SERVER_SYNC': False, 'RESOURCE_SERVER': {'url': 'http://localhost:8000'}, 'RESOURCE_SERVICE_PATH': "/foo"}, True),
        ({'DISABLE_RESOURCE_SERVER_SYNC': True, 'RESOURCE_SERVER': {'url': 'http://localhost:8000'}, 'RESOURCE_SERVICE_PATH': "/foo"}, False),
        ({'DISABLE_RESOURCE_SERVER_SYNC': True, 'RESOURCE_SERVER': {'url': 'http://localhost:8000'}, 'RESOURCE_SERVICE_PATH': ""}, False),
    ],
)
def test_should_reverse_sync(settings, new_settings, should_sync):
    """
    Test that we only reverse sync if we have a resource server and syncing is not disabled.
    """
    for key, value in new_settings.items():
        setattr(settings, key, value)

    assert handlers._should_reverse_sync() == should_sync
