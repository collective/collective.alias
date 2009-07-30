import unittest

from Products.PloneTestCase.ptc import PloneTestCase
from collective.alias.tests.layer import Layer

from zope.component import getUtility
from zope.interface import alsoProvides

from z3c.relationfield import RelationValue
from zope.intid.interfaces import IIntIds

from collective.alias.interfaces import IAliasInformation
from collective.alias.interfaces import IHasAlias

class TestAliasing(PloneTestCase):
    
    layer = Layer
    
    def afterSetUp(self):
        self.intids = getUtility(IIntIds)
        
        self.folder.invokeFactory('Document', 'd1')
        self.folder['d1'].setTitle("Document one")
        self.folder['d1'].setDescription("Document one description")
        self.folder['d1'].setText("<p>Document one body</p>")
    
    def test_lookup_no_alias(self):
        info = IAliasInformation(self.folder['d1'], None)
        self.assertEquals(None, info)
        
    def test_find_aliases_single(self):
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias', 'a1', _aliasTarget=relation)
        
        info = IAliasInformation(self.folder['d1'])
        
        aliases = list(info.findAliases())
        self.assertEquals(1, len(aliases))
        self.failUnless(aliases[0].aq_parent.aq_base is self.folder.aq_base)
        self.assertEquals(self.folder['a1'].getPhysicalPath(), aliases[0].getPhysicalPath())
    
    def test_find_aliases_multiple(self):
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias', 'a1', _aliasTarget=relation)
        
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias', 'a2', _aliasTarget=relation)
        
        info = IAliasInformation(self.folder['d1'])
        
        aliases = list(info.findAliases())
        self.assertEquals(2, len(aliases))
        
        self.failUnless(aliases[0].aq_parent.aq_base is self.folder.aq_base)
        self.assertEquals(self.folder['a1'].getPhysicalPath(), aliases[0].getPhysicalPath())
        
        self.failUnless(aliases[1].aq_parent.aq_base is self.folder.aq_base)
        self.assertEquals(self.folder['a2'].getPhysicalPath(), aliases[1].getPhysicalPath())
        
    def test_find_aliases_none(self):
        # dodgy IHasAlias marker
        alsoProvides(self.folder['d1'], IHasAlias)
        
        info = IAliasInformation(self.folder['d1'])
        aliases = list(info.findAliases())
        self.assertEquals(0, len(aliases))
    
    def test_find_ids_single(self):
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias', 'a1', _aliasTarget=relation)
        
        info = IAliasInformation(self.folder['d1'])
        
        aliases = list(info.findAliasIds())
        self.assertEquals(1, len(aliases))
        self.assertEquals(self.intids.getId(self.folder['a1']), aliases[0])
    
    def test_find_ids_multiple(self):
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias', 'a1', _aliasTarget=relation)
        
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias', 'a2', _aliasTarget=relation)
        
        info = IAliasInformation(self.folder['d1'])
        
        aliases = list(info.findAliasIds())
        self.assertEquals(2, len(aliases))
        self.assertEquals(self.intids.getId(self.folder['a1']), aliases[0])
        self.assertEquals(self.intids.getId(self.folder['a2']), aliases[1])
        
    def test_find_ids_none(self):
        # dodgy IHasAlias marker
        alsoProvides(self.folder['d1'], IHasAlias)
        
        info = IAliasInformation(self.folder['d1'])
        aliases = list(info.findAliasIds())
        self.assertEquals(0, len(aliases))

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)