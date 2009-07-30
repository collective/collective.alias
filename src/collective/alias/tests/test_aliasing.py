import unittest

from Products.PloneTestCase.ptc import PloneTestCase
from Products.Five.security import newInteraction

from collective.alias.tests.layer import Layer

from zope.component import getUtility
from zope.component import provideHandler
from zope.component import getGlobalSiteManager

from zope.interface import Interface

from zope import schema

from zope.security import checkPermission
from zope.annotation.interfaces import IAnnotations

from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.lifecycleevent import modified

from z3c.relationfield import RelationValue
from zope.intid.interfaces import IIntIds

from Products.ATContentTypes.interface import IATDocument
from Products.CMFCore.utils import getToolByName

from collective.alias.interfaces import IAlias
from collective.alias.interfaces import IHasAlias

from plone.dexterity.fti import DexterityFTI

events_received = []
def object_event_handler(obj, event):
    global events_received
    events_received.append((obj, event))

class ITest(Interface):
    
    title = schema.TextLine(title=u"Title")
    foo = schema.Text(title=u"Foo")

class TestAliasing(PloneTestCase):
    
    layer = Layer
    
    def afterSetUp(self):
        global events_received
        events_received = []
        
        newInteraction() # workaround for problem with checkPermission

        self.intids = getUtility(IIntIds)
        
        self.folder.invokeFactory('Document', 'd1')
        self.folder['d1'].setTitle("Document one")
        self.folder['d1'].setDescription("Document one description")
        self.folder['d1'].setText("<p>Document one body</p>")
        
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias', 'a1', _aliasTarget=relation)
    
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
        self.folder.invokeFactory('collective.alias', 'a2', _aliasTarget=relation)
        
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
        self.folder.invokeFactory('collective.alias', 'a2', _aliasTarget=relation)
        
        self.failUnless(IHasAlias.providedBy(self.folder['d1']))
        self.folder._delObject('a1')
        self.failUnless(IHasAlias.providedBy(self.folder['d1']))
        self.folder._delObject('a2')
        self.failIf(IHasAlias.providedBy(self.folder['d1']))
    
    def test_has_alias_counter_down(self):
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias', 'a2', _aliasTarget=relation)
        
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
        self.folder.invokeFactory('collective.alias', 'a2', _aliasTarget=relation)
        self.failUnless(self.folder['a1']._target.aq_base is self.folder['a2']._target.aq_base)

    def test_title_override(self):
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias', 'a2', _aliasTarget=relation, _aliasTitle=u"Title override")
        self.assertEquals("Title override", self.folder['a2'].Title())
        self.assertEquals("Title override", self.folder['a2'].title)
        
        self.assertEquals("Document one description", self.folder['a2'].Description())
        self.assertEquals("<p>Document one body</p>", self.folder['a2'].getText())
        
    def test_folderishness(self):
        self.failIf(self.folder['a1'].isPrincipiaFolderish)
        
        self.folder.invokeFactory('Folder', 'f1')
        relation = RelationValue(self.intids.getId(self.folder['f1']))
        self.folder.invokeFactory('collective.alias', 'a2', _aliasTarget=relation)
        self.failUnless(self.folder['a2'].isPrincipiaFolderish)
    
    def test_alias_traversal(self):
        self.folder.invokeFactory('Folder', 'f1')
        relation = RelationValue(self.intids.getId(self.folder['f1']))
        
        self.folder['f1'].invokeFactory('Document', 'd11')
        
        self.folder.invokeFactory('collective.alias', 'a2', _aliasTarget=relation)
        self.assertRaises(KeyError, self.folder['a1'].__getitem__, 'd11')
        
        self.folder['a2']._aliasTraversal = True
        self.failUnless(self.folder['a2']['d11'].aq_base, self.folder['f1']['d11'].aq_base)
        
    def test_alias_child(self):
        self.folder.invokeFactory('Folder', 'f1')
        
        relation = RelationValue(self.intids.getId(self.folder['f1']))
        self.folder.invokeFactory('collective.alias', 'a2', _aliasTarget=relation)
        
        self.folder['a2'].invokeFactory('Document', 'd21')
        self.assertEquals(self.folder['a2'].absolute_url() + '/d21',
                          self.folder['a2']['d21'].absolute_url())
    
    def test_permissions_not_aliased(self):
        self.failUnless(checkPermission('zope2.View', self.folder['d1']))
        self.folder['d1'].manage_permission('View', roles=['Manager'])
        self.failIf(checkPermission('zope2.View', self.folder['d1']))
        self.failUnless(checkPermission('zope2.View', self.folder['a1']))
    
    def test_workflow_not_aliased_change_target(self):
        self.setRoles(['Manager'])
        wf = getToolByName(self.portal, 'portal_workflow')
        
        self.assertEquals('private', wf.getInfoFor(self.folder['d1'], 'review_state'))
        self.assertEquals('private', wf.getInfoFor(self.folder['a1'], 'review_state'))
        
        wf.doActionFor(self.folder['d1'], 'publish')
        
        self.assertEquals('published', wf.getInfoFor(self.folder['d1'], 'review_state'))
        self.assertEquals('private', wf.getInfoFor(self.folder['a1'], 'review_state'))
    
    def test_workflow_not_aliased_change_alias(self):
        self.setRoles(['Manager'])
        wf = getToolByName(self.portal, 'portal_workflow')
        
        self.assertEquals('private', wf.getInfoFor(self.folder['d1'], 'review_state'))
        self.assertEquals('private', wf.getInfoFor(self.folder['a1'], 'review_state'))
        
        wf.doActionFor(self.folder['a1'], 'publish')
        
        self.assertEquals('private', wf.getInfoFor(self.folder['d1'], 'review_state'))
        self.assertEquals('published', wf.getInfoFor(self.folder['a1'], 'review_state'))
    
    def test_workflow_chain_aliased(self):
        wf = getToolByName(self.portal, 'portal_workflow')
        wf.setChainForPortalTypes(('collective.alias',), ())
        
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias', 'a2', _aliasTarget=relation)
        
        self.assertEquals(('simple_publication_workflow',), wf.getChainFor(self.folder['a2']))
    
    def test_workflow_initial_state(self):
        wf = getToolByName(self.portal, 'portal_workflow')
        
        self.assertEquals(('simple_publication_workflow',), wf.getChainFor(self.folder['d1']))
        wf['simple_publication_workflow'].initial_state = 'published'
        
        relation = RelationValue(self.intids.getId(self.folder['d1']))
        self.folder.invokeFactory('collective.alias', 'a2', _aliasTarget=relation)
        
        self.assertEquals('private', wf.getInfoFor(self.folder['a1'], 'review_state'))
        self.assertEquals('private', wf.getInfoFor(self.folder['d1'], 'review_state'))
        self.assertEquals('published', wf.getInfoFor(self.folder['a2'], 'review_state'))
    
    def test_display_templates(self):
        self.folder.invokeFactory('Folder', 'f1')
        
        relation = RelationValue(self.intids.getId(self.folder['f1']))
        self.folder.invokeFactory('collective.alias', 'a2', _aliasTarget=relation)
        
        self.folder['f1'].setLayout('folder_tabular_view')
        self.assertEquals('folder_tabular_view', self.folder['f1'].getLayout())
        self.assertEquals('folder_tabular_view', self.folder['a2'].getLayout())
        
        self.folder['a2'].setLayout('folder_listing')
        self.assertEquals('folder_tabular_view', self.folder['f1'].getLayout())
        self.assertEquals('folder_listing', self.folder['a2'].getLayout())
    
    def test_annotations(self):
        d1 = IAnnotations(self.folder['d1'])
        a1 = IAnnotations(self.folder['a1'])
        
        d1['test.key1'] = 1
        self.assertEquals(1, a1['test.key1'])
        
        a1['test.key2'] = 2
        self.assertEquals(2, a1['test.key2'])
        self.failIf('test.key2' in d1)
        
        a1['test.key1'] = 3
        self.assertEquals(1, d1['test.key1'])
        self.assertEquals(3, a1['test.key1'])
    
    def test_modified_event_rebroadcast(self):
        provideHandler(object_event_handler, (IAlias, IObjectModifiedEvent,))
        
        modified(self.folder['d1'])
        
        self.assertEquals(1, len(events_received))
        self.failUnless(self.folder['a1'].aq_base is events_received[0][0].aq_base)
        
        sm = getGlobalSiteManager()
        sm.unregisterHandler(object_event_handler, required=(IAlias, IObjectModifiedEvent,))
    
    def test_comments(self):
        pd = getToolByName(self.portal, 'portal_discussion')
        
        self.folder['d1'].getTypeInfo().allow_discussion = True
        
        discussion = pd.getDiscussionFor(self.folder['d1'])
        discussion.createReply("Reply 1", "Some text")
        
        discussion = pd.getDiscussionFor(self.folder['a1'])
        
        self.assertEquals(1, discussion.replyCount(self.folder['a1']))
        self.assertEquals("Reply 1", discussion.getReplies()[0].title)

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)