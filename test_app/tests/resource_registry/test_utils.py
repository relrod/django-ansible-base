from contextlib import contextmanager
from unittest import mock

import pytest
from crum import impersonate
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
from rest_framework.exceptions import ValidationError

from ansible_base.resource_registry import apps
from test_app.models import Organization

handlers_path = 'ansible_base.resource_registry.signals.handlers'
utils_path = 'ansible_base.resource_registry.utils.sync_to_resource_server'


@pytest.fixture
def connect_monkeypatch(settings):
    @contextmanager
    def f():
        # This is kind of a dance. We don't want to break other tests by
        # leaving the save method monkeypatched when they are expecting syncing
        # to be disabled. So we patch the save method, yield, reset
        # DISABLE_RESOURCE_SERVER_SYNC, undo the patch (disconnect_resource_signals),
        # and then reconnect signals (so the resource registry stuff still works) but
        # this time we don't monkeypatch the save method since DISABLE_RESOURCE_SERVER_SYNC
        # is back to its original value.
        is_disabled = settings.DISABLE_RESOURCE_SERVER_SYNC
        settings.DISABLE_RESOURCE_SERVER_SYNC = False
        apps.connect_resource_signals(sender=None)
        yield
        apps.disconnect_resource_signals(sender=None)
        settings.DISABLE_RESOURCE_SERVER_SYNC = is_disabled
        apps.connect_resource_signals(sender=None)

    return f


class TestReverseResourceSync:
    @pytest.mark.django_db(transaction=True)
    @pytest.mark.parametrize('action', ['create', 'update', 'delete'])
    def test_sync_to_resource_server_happy_path(self, user, action, connect_monkeypatch):
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
        if action in ('delete', 'update'):
            # If we're updating or deleting, we need an existing object,
            # create it before we start patching and tracking queries
            org = Organization.objects.create(name='Hello')

        with connect_monkeypatch():
            with mock.patch(f'{utils_path}.get_resource_server_client') as get_resource_server_client:
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
        client_method.assert_called()

        # The whole thing is wrapped in a transaction
        assert queries.captured_queries[-1]['sql'] == 'COMMIT'

    @pytest.mark.django_db
    @pytest.mark.parametrize('anon', [AnonymousUser(), None])
    def test_sync_to_resource_server_unauthenticated(self, anon, connect_monkeypatch):
        """
        If we don't have a user (e.g. we are a CLI app) or somehow we are here but
        with an anonymous user, we should sync as the system user.
        """
        with connect_monkeypatch():
            with mock.patch(f'{utils_path}.get_resource_server_client') as get_resource_server_client:
                with impersonate(anon):
                    Organization.objects.create(name='Hello')

        # Assert one of the kwargs to get_resource_server_client was jwt_user_id=None
        assert any([kwargs.get('jwt_user_id') is None for args, kwargs in get_resource_server_client.call_args_list])

    @pytest.mark.django_db
    @pytest.mark.parametrize('nullify_resource', [pytest.param(True, id="resource is None"), pytest.param(False, id="resource is not None but does not exist")])
    def test_sync_to_resource_server_no_resource(self, user, nullify_resource, connect_monkeypatch):
        """
        Somehow we are trying to sync a model that doesn't have a resource associated
        with it. This should be a no-op.
        """
        with connect_monkeypatch():
            # Just mock this out so we don't create a resource on the object
            with mock.patch(f'{handlers_path}.init_resource_from_object'):
                org = Organization(name='Hello')
                if nullify_resource:
                    org.resource = None
                org.save()

                with mock.patch(f'{utils_path}.get_resource_server_client') as get_resource_server_client:
                    with impersonate(user):
                        org.name = 'World'
                        org.save()

        # We bail out if we don't have a resource
        get_resource_server_client.assert_not_called()

    @pytest.mark.django_db(transaction=True)
    def test_sync_to_resource_server_exception_during_sync(self, user, connect_monkeypatch):
        """
        We get an exception when trying to sync (e.g. the server gives us a 500, or
        we can't connect, etc.). We raise ValidationError and don't commit the change.
        """
        with connect_monkeypatch():
            with mock.patch(f'{utils_path}.get_resource_server_client') as get_resource_server_client:
                get_resource_server_client.return_value.create_resource.side_effect = Exception('Boom!')
                with impersonate(user):
                    with CaptureQueriesContext(connection) as queries:
                        with pytest.raises(ValidationError, match="Failed to sync resource"):
                            Organization.objects.create(name='Hello')

        assert queries.captured_queries[-1]['sql'] == 'ROLLBACK'

    @pytest.mark.django_db(transaction=True)
    def test_sync_to_resource_server_exception_during_save(self, user, organization, connect_monkeypatch):
        """
        If we get an exception during .save(), the transaction should still roll back
        and nothing should get synced to the resource server.
        """
        with connect_monkeypatch():
            with mock.patch(f'{utils_path}.get_resource_server_client'):
                with impersonate(user):
                    with CaptureQueriesContext(connection) as queries:
                        with pytest.raises(IntegrityError):
                            org = Organization(name=organization.name)
                            org.save()

        assert queries.captured_queries[-1]['sql'] == 'ROLLBACK'

    @pytest.mark.django_db(transaction=True)
    def test_sync_to_resource_server_from_resource_server(self, user, organization, connect_monkeypatch):
        """
        If we try to sync a model that came from the resource server, we should bail out.
        """
        with connect_monkeypatch():
            with mock.patch(f'{utils_path}.get_resource_server_client') as get_resource_server_client:
                organization._is_from_resource_server = True
                organization.save()

        get_resource_server_client.assert_not_called()

    @pytest.mark.parametrize(
        'new_settings,should_sync',
        [
            ({'DISABLE_RESOURCE_SERVER_SYNC': False, 'RESOURCE_SERVER': {}, 'RESOURCE_SERVICE_PATH': "/foo"}, False),
            ({'DISABLE_RESOURCE_SERVER_SYNC': False, 'RESOURCE_SERVER': {'url': 'http://localhost:8000'}, 'RESOURCE_SERVICE_PATH': "/foo"}, True),
            ({'DISABLE_RESOURCE_SERVER_SYNC': True, 'RESOURCE_SERVER': {'url': 'http://localhost:8000'}, 'RESOURCE_SERVICE_PATH': "/foo"}, False),
            ({'DISABLE_RESOURCE_SERVER_SYNC': True, 'RESOURCE_SERVER': {'url': 'http://localhost:8000'}, 'RESOURCE_SERVICE_PATH': ""}, False),
        ],
    )
    def test_should_reverse_sync(self, settings, new_settings, should_sync):
        """
        Test that we only reverse sync if we have a resource server and syncing is not disabled.
        """
        for key, value in new_settings.items():
            setattr(settings, key, value)

        assert apps._should_reverse_sync() == should_sync
