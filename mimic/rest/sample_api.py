from twisted.plugin import IPlugin
from mimic.imimic import IAPIMock
from mimic.catalog import Entry
from mimic.catalog import Endpoint
from zope.interface import implementer
from six import text_type
from uuid import uuid4
from mimic.rest.mimicapp import MimicApp
import json
from twisted.web.server import Request


Request.defaultContentType = 'application/json'


@implementer(IAPIMock, IPlugin)
class SampleApi(object):
    """
    Rest endpoints for mocked Sample Api.
    """

    def catalog_entries(self, tenant_id):
        """
        List catalog entries for the Nova API.
        """
        return [
            Entry(
                tenant_id, "staging", "cloudSampleApi",
                [
                    Endpoint(tenant_id, "ORD", text_type(uuid4()), prefix="v2"),
                    Endpoint(tenant_id, "DFW", text_type(uuid4()), prefix="v3")
                ]
            )
        ]

    def resource_for_region(self, uri_prefix):
        """
        Get an :obj:`twisted.web.iweb.IResource` for the given URI prefix;
        implement :obj:`IAPIMock`.
        """
        return SampleMock(uri_prefix).app.resource()


class SampleMock(object):

    app = MimicApp()

    def __init__(self, uri_prefix):
        """
        Create a nova region with a given URI prefix (used for generating URIs
        to servers).
        """
        self.uri_prefix = uri_prefix

    @app.route("/v2/<string:tenant_id>/sample", methods=['GET'])
    def sample_mock(self, request, tenant_id):
        return json.dumps({"sample": []})
