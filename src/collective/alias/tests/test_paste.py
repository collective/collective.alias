import unittest

from Products.PloneTestCase.ptc import PloneTestCase
from collective.alias.tests.layer import Layer

from zope.component import getUtility

from plone.registry.interfaces import IRegistry
from collective.alias.interfaces import IAliasSettings

from collective.alias.paste import pasteAsAlias

class TestSetup(PloneTestCase):
    
    layer = Layer
    
    def test_paste_single(self):
        self.folder.invokeFactory('Folder', 'source')
        self.folder.invokeFactory('Folder', 'dest')
        
        self.folder['source'].invokeFactory('Document', 'd1')
        
        data = self.folder['source'].manage_copyObjects(('d1',))
        pasteAsAlias(self.folder['dest'], data)
        
        alias = self.folder['dest']['d1']
        self.failUnless(alias.isAlias)
        
        self.failUnless(alias._target.aq_base is self.folder['source']['d1'].aq_base)
    
    def test_paste_multiple(self):
        self.folder.invokeFactory('Folder', 'source')
        self.folder.invokeFactory('Folder', 'dest')
        
        self.folder['source'].invokeFactory('Document', 'd1')
        self.folder['source'].invokeFactory('Document', 'd2')
        
        data = self.folder['source'].manage_copyObjects(('d1', 'd2',))
        pasteAsAlias(self.folder['dest'], data)
        
        alias1 = self.folder['dest']['d1']
        self.failUnless(alias1.isAlias)
        self.failUnless(alias1._target.aq_base is self.folder['source']['d1'].aq_base)
        
        alias2 = self.folder['dest']['d2']
        self.failUnless(alias2.isAlias)
        self.failUnless(alias2._target.aq_base is self.folder['source']['d2'].aq_base)
        
    def test_paste_same_directory(self):
        self.folder.invokeFactory('Folder', 'source')
        
        self.folder['source'].invokeFactory('Document', 'd1')
        
        data = self.folder['source'].manage_copyObjects(('d1',))
        pasteAsAlias(self.folder['source'], data)
        
        alias = self.folder['source']['d1-1']
        self.failUnless(alias.isAlias)
        
        self.failUnless(alias._target.aq_base is self.folder['source']['d1'].aq_base)
    
    def test_paste_traversal(self):
        
        settings = getUtility(IRegistry).forInterface(IAliasSettings)
        settings.traversalTypes = ['Folder']
        
        self.folder.invokeFactory('Folder', 'source')
        self.folder.invokeFactory('Folder', 'dest')
        
        self.folder['source'].invokeFactory('Document', 'd1')
        self.folder['source'].invokeFactory('Folder', 'f1')
        
        data = self.folder['source'].manage_copyObjects(('d1', 'f1',))
        pasteAsAlias(self.folder['dest'], data)
        
        alias1 = self.folder['dest']['d1']
        self.failUnless(alias1.isAlias)
        self.failUnless(alias1._target.aq_base is self.folder['source']['d1'].aq_base)
        self.assertEquals(False, alias1._aliasTraversal)
        
        alias2 = self.folder['dest']['f1']
        self.failUnless(alias2.isAlias)
        self.failUnless(alias2._target.aq_base is self.folder['source']['f1'].aq_base)
        self.assertEquals(True, alias2._aliasTraversal)
    
def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)