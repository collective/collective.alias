import unittest

from Products.PloneTestCase.ptc import PloneTestCase
from collective.alias.tests.layer import Layer

from zope.component import getUtility

from z3c.relationfield import RelationValue
from zope.intid.interfaces import IIntIds

from Products.ATContentTypes.interface import IATDocument
from Products.CMFCore.utils import getToolByName

from collective.alias.interfaces import IAlias
from collective.alias.interfaces import IHasAlias

from plone.dexterity.fti import DexterityFTI

from zope.interface import Interface
from zope import schema

class ITest(Interface):
    
    title = schema.TextLine(title=u"Title")
    foo = schema.Text(title=u"Foo")

class TestAliasing(PloneTestCase):
    
    layer = Layer
    
    def afterSetUp(self):
        self.intids = getUtility(IIntIds)
        
        self.folder.invokeFactory('Document', 'd1')
        self.folder['d1'].setTitle("Document one")
        self.folder['d1'].setDescription("Document one description")
        self.folder['d1'].setText("<p>Document one body</p>")
        
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias.alias', 'a1', _aliasTarget=relation)
    
    def test_alias_archetypes_object(self):
        self.failUnless(self.folder['a1'].isAlias)
        
        self.assertEquals("Document one", self.folder['a1'].Title())
        self.assertEquals("Document one", self.folder['a1'].title)
        
        self.assertEquals("Document one description", self.folder['a1'].Description())
        self.assertEquals("<p>Document one body</p>", self.folder['a1'].getText())
    
    def test_alias_dexterity_object(self):
        tt = getToolByName(self.portal, 'portal_types')
        
        fti = DexterityFTI('collective.alias.test')
        fti.schema = ITest.__identifier__
        
        tt._setObject('collective.alias.test', fti)
        
        self.folder.invokeFactory('collective.alias.test', 't1')
        self.folder['t1'].title = "Dummy title"
        self.folder['t1'].foo = "Foo Bar"
        
        relation = RelationValue(self.intids.getId(self.folder['t1']))
        self.folder.invokeFactory('collective.alias.alias', 'a2', _aliasTarget=relation)
        
        self.failUnless(ITest.providedBy(self.folder['a2']))
        self.assertEquals("Dummy title", self.folder['a2'].title)
        self.assertEquals("Foo Bar", self.folder['a2'].foo)
    
    def test_portal_type(self):
        self.assertEquals('Document', self.folder['a1'].portal_type)
    
    def test_alias_interfaces(self):
        self.failUnless(IATDocument.providedBy(self.folder['a1']))
        self.failUnless(IAlias.providedBy(self.folder['a1']))
        self.failIf(IAlias.providedBy(self.folder['d1']))
    
    def test_has_alias(self):
        self.folder.invokeFactory('Document', 'd2')
        self.failIf(IHasAlias.providedBy(self.folder['d2']))
        self.failUnless(IHasAlias.providedBy(self.folder['d1']))
    
    def test_has_alias_removed_on_delete(self):
        self.failUnless(IHasAlias.providedBy(self.folder['d1']))
        self.folder._delObject('a1')
        self.failIf(IHasAlias.providedBy(self.folder['d1']))
    
    def test_has_alias_counter_up(self):
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias.alias', 'a2', _aliasTarget=relation)
        
        self.failUnless(IHasAlias.providedBy(self.folder['d1']))
        self.folder._delObject('a1')
        self.failUnless(IHasAlias.providedBy(self.folder['d1']))
        self.folder._delObject('a2')
        self.failIf(IHasAlias.providedBy(self.folder['d1']))
    
    def test_has_alias_counter_down(self):
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias.alias', 'a2', _aliasTarget=relation)
        
        self.failUnless(IHasAlias.providedBy(self.folder['d1']))
        self.folder._delObject('a2')
        self.failUnless(IHasAlias.providedBy(self.folder['d1']))
        self.folder._delObject('a1')
        self.failIf(IHasAlias.providedBy(self.folder['d1']))
    
    def test_has_alias_clone_loses_marker(self):
        self.failUnless(IHasAlias.providedBy(self.folder['d1']))
        cp = self.folder.manage_copyObjects('d1')
        result = self.folder.manage_pasteObjects(cp)
        self.assertEquals(1, len(result))
        newId = result[0]['new_id']
        self.failUnless(IHasAlias.providedBy(self.folder['d1']))
        self.failIf(IHasAlias.providedBy(self.folder[newId]))
    
    def test_transitive_alias(self):
        relation = RelationValue(self.intids.getId(self.folder['a1']))
        self.folder.invokeFactory('collective.alias.alias', 'a2', _aliasTarget=relation)
        self.failUnless(self.folder['a1']._target.aq_base is self.folder['a2']._target.aq_base)

    def test_title_override(self):
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias.alias', 'a2', _aliasTarget=relation, _aliasTitle=u"Title override")
        self.assertEquals("Title override", self.folder['a2'].Title())
        self.assertEquals("Title override", self.folder['a2'].title)
        
        self.assertEquals("Document one description", self.folder['a2'].Description())
        self.assertEquals("<p>Document one body</p>", self.folder['a2'].getText())
        
    def test_folderishness(self):
        self.failIf(self.folder['a1'].isPrincipiaFolderish)
        
        self.folder.invokeFactory('Folder', 'f1')
        relation = RelationValue(self.intids.getId(self.folder['f1']))
        self.folder.invokeFactory('collective.alias.alias', 'a2', _aliasTarget=relation)
        self.failUnless(self.folder['a2'].isPrincipiaFolderish)
    
    def test_alias_traversal(self):
        pass
    
    def test_permissions(self):
        pass
    
    def test_display_templates(self):
        pass
    
    def test_annotations(self):
        pass
    
    def test_modified_event_rebroadcast(self):
        pass
    
    def test_name_chooser(self):
        pass
    
    def test_talkback(self):
        pass
    
def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)