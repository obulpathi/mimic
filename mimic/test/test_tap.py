"""
Tests for L{mimic.tap}
"""

import sys
import types

from zope.interface import implementer

from twisted import plugins

from twisted.internet.interfaces import (
    IStreamServerEndpointStringParser, IStreamServerEndpoint
)
from twisted.internet.defer import succeed

from twisted.plugin import IPlugin
from twisted.python.filepath import FilePath

from twisted.trial.unittest import SynchronousTestCase

from mimic.core import MimicCore
from mimic.tap import Options, makeService


@implementer(IStreamServerEndpoint)
class FakeEndpoint(object):
    """
    A fake endpoint that records the factories it's listening on.
    """
    def __init__(self):
        """
        Create a list of factories.
        """
        self.factories = []

    def listen(self, factory):
        """
        Store the factory.
        """
        return succeed(self.factories.append(factory))


@implementer(IPlugin)
@implementer(IStreamServerEndpointStringParser)
class FakeEndpointParser(object):
    """
    Fake Endpoint Parser.
    """

    prefix = 'fake'

    def __init__(self):
        """
        Create a list of endpoints.
        """
        self.endpoints = []

    def parseStreamServer(self, reactor, *args, **kwargs):
        """
        Construct a :obj:`FakeEndpoint` and remember it.
        """
        self.endpoints.append(FakeEndpoint())
        return self.endpoints[-1]


def addFakePluginObject(testCase, pluginPackage, pluginObject):
    """
    Add a fake plugin for the duration of the given test.
    """
    dropinName = "a_fake_dropin"
    dropinQualifiedName = pluginPackage.__name__ + "." + dropinName
    module = sys.modules[dropinQualifiedName] = types.ModuleType(
        dropinQualifiedName)
    testCase.addCleanup(lambda: sys.modules.pop(dropinQualifiedName))
    setattr(pluginPackage, dropinName, module)
    testCase.addCleanup(lambda: delattr(pluginPackage, dropinName))
    # Should provide relevant plugin interface, IPlugin
    module.a_plugin = pluginObject
    tempDir = testCase.mktemp()
    fp = FilePath(tempDir)
    fp.createDirectory()
    pluginPackage.__path__.append(tempDir)
    fp.child("a_fake_dropin.py").touch()


class TapTests(SynchronousTestCase):
    """
    Tests for L{mimic.tap}
    """

    def test_listenOption(self):
        """
        Listen options.
        """
        o = Options()
        o.parseOptions(["--listen", "4321"])
        self.assertEqual(o["listen"], "4321")

    def test_makeService(self):
        """
        makeService creates a service that, when listened upon, creates a Site.
        """
        o = Options()
        o.parseOptions(["--listen", "fake:"])
        thisFakeParser = FakeEndpointParser()
        addFakePluginObject(self, plugins, thisFakeParser)
        service = makeService(o)
        service.startService()
        self.assertEqual(len(thisFakeParser.endpoints), 1)
        endpoints = thisFakeParser.endpoints[0]
        self.assertEqual(len(endpoints.factories), 1)
        factory = endpoints.factories[0]
        self.assertEqual(factory.displayTracebacks, False)

    def test_realtime(self):
        """
        The C{--realtime} option specifies that the global reactor ought to be
        used, so Mimic's time can be advanced by the passage of real time.
        """
        o = Options()
        o.parseOptions(["--realtime"])

        class CheckClock(MimicCore):
            @classmethod
            def fromPlugins(cls, clock):
                result = super(CheckClock, cls).fromPlugins(clock)
                CheckClock.clock = clock
                return result
        from mimic import tap
        self.patch(tap, "MimicCore", CheckClock)
        makeService(o)
        # Grab the global reactor just for comparison.
        from twisted.internet import reactor as real_reactor
        self.assertIdentical(CheckClock.clock, real_reactor)
