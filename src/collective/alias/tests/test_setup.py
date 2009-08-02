import unittest

from Products.PloneTestCase.ptc import PloneTestCase
from collective.alias.tests.layer import Layer

from zope.component import getUtility
from Products.CMFCore.utils import getToolByName
from plone.registry.interfaces import IRegistry
from collective.alias.interfaces import IAliasSettings


class TestSetup(PloneTestCase):
    
    layer = Layer
    
    def test_type_installed(self):
        tt = getToolByName(self.portal, 'portal_types')
        self.failUnless('collective.alias' in tt.objectIds())
    
    def test_action_installed(self):
        at = getToolByName(self.portal, 'portal_actions')
        self.failUnless('paste_alias' in at['object_buttons'])
    
    def test_registry_records_installed(self):
        reg = getUtility(IRegistry)
        records = reg.forInterface(IAliasSettings)
        self.failUnless('Topic' in records.traversalTypes)
        self.failUnless('view' in records.aliasActions)

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)