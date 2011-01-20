from rwproperty import getproperty, setproperty

from five import grok
from plone.directives import dexterity

from zope.component import getUtility
from zope.component import getMultiAdapter

from zope.app.container.interfaces import INameChooser
from plone.dexterity.interfaces import IDexterityFTI

from Acquisition import aq_inner
from AccessControl import Unauthorized

from plone.app.layout.viewlets.interfaces import IContentViews

from plone.registry.interfaces import IRegistry

from collective.alias.interfaces import IAlias
from collective.alias.interfaces import IAliasSettings

from collective.alias import MessageFactory as _

class Add(dexterity.AddForm):
    """Override the add form not to depend on the portal_type once the
    object has been created.
    """
    
    grok.name('collective.alias')
    
    def add(self, object):
        
        fti = getUtility(IDexterityFTI, name=self.portal_type)
        container = aq_inner(self.context)
        container = aq_inner(container)
        
        container_fti = container.getTypeInfo()
        
        if not fti.isConstructionAllowed(container):
            raise Unauthorized("Cannot create %s" % self.portal_type)
        
        if container_fti is not None and not container_fti.allowType(self.portal_type):
            raise ValueError("Disallowed subobject type: %s" % self.portal_type)
        
        target = aq_inner(object._target)
        name = None
        if target is not None:
            name = target.getId()
        
        name = INameChooser(container).chooseName(name, object)
        object.id = name
        
        new_name = container._setObject(name, object)
        
        # XXX: When we move to CMF 2.2, an event handler will take care of this
        new_object = container._getOb(new_name)
        new_object.notifyWorkflowCreated()
        
        immediate_view = fti.immediate_view or 'view'
        self.immediate_view = "%s/%s/%s" % (container.absolute_url(), new_object.id, immediate_view,)
    
    def updateFields(self):
        super(Add, self).updateFields()
        
        # Don't set the traversal flag on the add form: we default by
        # portal type once we know what the portal type is
        if '_aliasTraversal' in self.fields:
            del self.fields['_aliasTraversal']

class Edit(dexterity.EditForm):
    """Override the edit form not to depend on the portal_type
    """
    
    grok.context(IAlias)
    grok.name('edit')
    
    label = _(u"Edit alias")
    
    @getproperty
    def portal_type(self):
        return self.context._alias_portal_type
    
    @setproperty
    def portal_type(self, value):
        """Evil hack. The base class tries to set this in a way that's not
        trivial to override. Just ignore it. :)
        """
        pass
    
    def updateFields(self):
        super(Edit, self).updateFields()
        
        # Don't allow the alias to be edited - it causes all kinds of confusion
        if '_aliasTarget' in self.fields:
            del self.fields['_aliasTarget']

class ContentViews(grok.Viewlet):
    """Override the content views (edit tabs) viewlet to ensure that we only
    get the "edit" action for the alias.
    """
    
    grok.context(IAlias)
    grok.require('zope2.View')
    grok.name('plone.contentviews')
    grok.viewletmanager(IContentViews)
    
    def update(self):
        
        context = aq_inner(self.context)
        ploneview = getMultiAdapter((context, self.request,), name=u"plone")
        
        settings = getUtility(IRegistry).forInterface(IAliasSettings)
        allowedActions = settings.aliasActions
        
        self.showEditableBorder = ploneview.showEditableBorder()
        actions = [] #ploneview.prepareObjectTabs()
        
        contextURL = context.absolute_url()
        
        requestURL = self.request['ACTUAL_URL']
        requestURLPath = requestURL[len(contextURL):]
        if requestURLPath.startswith('/'):
            requestURLPath = requestURLPath[1:]
        
        is_edit = requestURLPath in ('edit', '@@edit',)
        
        self.actions = []
        
        for a in actions:
            if a['id'] not in allowedActions:
                continue
            
            if a['id'] == 'edit':
                a['url'] = "%s/@@edit" % contextURL
                a['selected'] = is_edit
            else:
                if is_edit:
                    a['selected'] = False
        
            self.actions.append(a)
