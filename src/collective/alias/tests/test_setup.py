import unittest

from Products.PloneTestCase.ptc import PloneTestCase
from collective.alias.tests.layer import Layer

from Products.CMFCore.utils import getToolByName

class TestSetup(PloneTestCase):
    
    layer = Layer
    
    def test_type_installed(self):
        tt = getToolByName(self.portal, 'portal_types')
        self.failUnless('collective.alias' in tt.objectIds())

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)