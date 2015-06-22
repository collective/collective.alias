import unittest

from Products.PloneTestCase.ptc import PloneTestCase
from collective.alias.tests.layer import Layer

from zope.component import getUtility
from zope.component.interface import interfaceToName
from zope import interface
from Products.CMFCore.utils import getToolByName
from plone.registry.interfaces import IRegistry
from collective.alias.interfaces import IAliasSettings
from collective.alias.interfaces import IHasAlias
from z3c.relationfield import RelationValue
from zope.intid.interfaces import IIntIds


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
        self.failUnless('Collection' in records.traversalTypes)
        self.failUnless('view' in records.aliasActions)

    def test_uninstall(self):
        pid = 'collective.alias'
        self.folder.invokeFactory('Document', 'd1')
        self.folder['d1'].setTitle("Document one")
        self.folder['d1'].setDescription("Document one description")
        self.folder['d1'].setText("<p>Document one body</p>")

        intids = getUtility(IIntIds)

        relation = RelationValue(intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias', 'a1', _aliasTarget=relation)
        self.folder["d1"].reindexObject()
        self.assertTrue(IHasAlias.providedBy(self.folder['d1']))

        qi_tool = getToolByName(self.portal, 'portal_quickinstaller')
        qi_tool.uninstallProducts([pid])
        self.assertFalse(qi_tool.isProductInstalled(pid))
        self.folder["d1"].reindexObject()
        self.assertFalse(IHasAlias.providedBy(self.folder['d1']))


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)