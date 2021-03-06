# -*- test-case-name: mimic.test.test_loadbalancer -*-
"""
Defines add node and delete node from load balancers
"""
from collections import defaultdict
import json
from uuid import uuid4
from six import text_type
from zope.interface import implementer
from twisted.web.server import Request
from twisted.plugin import IPlugin
from mimic.canned_responses.loadbalancer import (
    Region_Tenant_CLBs,
    add_load_balancer, del_load_balancer, list_load_balancers,
    add_node, delete_node, list_nodes, get_load_balancers, get_nodes)
from mimic.rest.mimicapp import MimicApp
from mimic.imimic import IAPIMock
from mimic.catalog import Entry
from mimic.catalog import Endpoint
from random import randrange
from mimic.util.helper import invalid_resource


Request.defaultContentType = 'application/json'


@implementer(IAPIMock, IPlugin)
class LoadBalancerApi(object):
    """
    Rest endpoints for mocked Load balancer api.
    """
    def __init__(self, regions=["ORD"]):
        """
        Create an API with the specified regions.
        """
        self._regions = regions

    def catalog_entries(self, tenant_id):
        """
        Cloud load balancer entries.
        """
        # TODO: actually add some entries so load balancers show up in the
        # service catalog.
        return [
            Entry(tenant_id, "rax:load-balancer", "cloudLoadBalancers",
                  [
                      Endpoint(tenant_id, text_type(uuid4()), region,
                               prefix="v2")
                      for region in self._regions
                  ])
        ]

    def resource(self, uri_prefix, session_store, region=None):
        """
        Get an :obj:`twisted.web.iweb.IResource` for the given URI prefix;
        implement :obj:`IAPIMock`.
        """
        lb_region = LoadBalancerRegion(self, uri_prefix, session_store,
                                       region)
        return lb_region.app.resource()


class LoadBalancerRegion(object):
    """
    Klein routes for load balancer API methods within a particular region.
    """

    app = MimicApp()

    def __init__(self, api_mock, uri_prefix, session_store, region_name):
        """
        Fetches the load balancer id for a failure, invalid scenarios and
        the count on the number of time 422 should be returned on add node.
        """
        self.uri_prefix = uri_prefix
        self.region_name = region_name
        self._api_mock = api_mock
        self._session_store = session_store

    def session(self, tenant_id):
        """
        Gets a session for a particular tenant, creating one if there isn't
        one.
        """
        return (self._session_store.session_for_tenant_id(tenant_id)
                .data_for_api(self._api_mock,
                              lambda: defaultdict(Region_Tenant_CLBs))
                [self.region_name])

    @app.route('/v2/<string:tenant_id>/loadbalancers', methods=['POST'])
    def add_load_balancer(self, request, tenant_id):
        """
        Creates a load balancer and adds it to the load balancer store.
        Returns the newly created load balancer with response code 202
        """
        try:
            content = json.loads(request.content.read())
        except ValueError:
            request.setResponseCode(400)
            return json.dumps(invalid_resource("Invalid JSON request body"))

        lb_id = randrange(99999)
        response_data = add_load_balancer(tenant_id, self.session(tenant_id),
                                          content['loadBalancer'], lb_id,
                                          self._session_store.clock.seconds())
        request.setResponseCode(response_data[1])
        return json.dumps(response_data[0])

    @app.route('/v2/<string:tenant_id>/loadbalancers/<int:lb_id>', methods=['GET'])
    def get_load_balancers(self, request, tenant_id, lb_id):
        """
        Returns a list of all load balancers created using mimic with response code 200
        """
        response_data = get_load_balancers(
            self.session(tenant_id), lb_id,
            self._session_store.clock.seconds()
        )
        request.setResponseCode(response_data[1])
        return json.dumps(response_data[0])

    @app.route('/v2/<string:tenant_id>/loadbalancers', methods=['GET'])
    def list_load_balancers(self, request, tenant_id):
        """
        Returns a list of all load balancers created using mimic with response code 200
        """
        response_data = list_load_balancers(
            tenant_id, self.session(tenant_id),
            self._session_store.clock.seconds()
        )
        request.setResponseCode(response_data[1])
        return json.dumps(response_data[0])

    @app.route('/v2/<string:tenant_id>/loadbalancers/<int:lb_id>', methods=['DELETE'])
    def delete_load_balancer(self, request, tenant_id, lb_id):
        """
        Creates a load balancer and adds it to the load balancer store.
        Returns the newly created load balancer with response code 200
        """
        response_data = del_load_balancer(
            self.session(tenant_id),
            lb_id, self._session_store.clock.seconds()
        )
        request.setResponseCode(response_data[1])
        return json.dumps(response_data[0])

    @app.route('/v2/<string:tenant_id>/loadbalancers/<int:lb_id>/nodes', methods=['POST'])
    def add_node_to_load_balancer(self, request, tenant_id, lb_id):
        """
        Return a successful add node response with code 200
        """
        try:
            content = json.loads(request.content.read())
        except ValueError:
            request.setResponseCode(400)
            return json.dumps(invalid_resource("Invalid JSON request body"))

        node_list = content['nodes']
        response_data = add_node(
            self.session(tenant_id), node_list, lb_id,
            self._session_store.clock.seconds()
        )
        request.setResponseCode(response_data[1])
        return json.dumps(response_data[0])

    @app.route('/v2/<string:tenant_id>/loadbalancers/<int:lb_id>/nodes/<int:node_id>',
               methods=['GET'])
    def get_nodes(self, request, tenant_id, lb_id, node_id):
        """
        Returns a 200 response code and list of nodes on the load balancer
        """
        response_data = get_nodes(
            self.session(tenant_id), lb_id, node_id,
            self._session_store.clock.seconds()
        )
        request.setResponseCode(response_data[1])
        return json.dumps(response_data[0])

    @app.route('/v2/<string:tenant_id>/loadbalancers/<int:lb_id>/nodes/<int:node_id>',
               methods=['DELETE'])
    def delete_node_from_load_balancer(self, request, tenant_id, lb_id, node_id):
        """
        Returns a 204 response code, for any load balancer created using the mocks
        """
        response_data = delete_node(
            self.session(tenant_id), lb_id, node_id,
            self._session_store.clock.seconds()
        )
        request.setResponseCode(response_data[1])
        return json.dumps(response_data[0])

    @app.route('/v2/<string:tenant_id>/loadbalancers/<int:lb_id>/nodes',
               methods=['GET'])
    def list_nodes_for_load_balancer(self, request, tenant_id, lb_id):
        """
        Returns a 200 response code and list of nodes on the load balancer
        """
        response_data = list_nodes(self.session(tenant_id), lb_id,
                                   self._session_store.clock.seconds())
        request.setResponseCode(response_data[1])
        return json.dumps(response_data[0])
