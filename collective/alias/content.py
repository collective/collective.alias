from rwproperty import getproperty, setproperty

from five import grok
from plone.directives import form, dexterity

from zope.interface.declarations import implementedBy
from zope.interface.declarations import getObjectSpecification
from zope.interface.declarations import ObjectSpecificationDescriptor

from zope.component import getUtility

from zope.app.component.hooks import getSite
from zope.app.publication.interfaces import IEndRequestEvent

from zope.annotation.interfaces import IAnnotations

from zope.lifecycleevent.interfaces import IObjectModifiedEvent

# XXX: Should move to zope.container in the future
from zope.app.container.interfaces import INameChooser
from zope.app.container.contained import Contained

from z3c.relationfield.schema import RelationChoice
from z3c.relationfield.interfaces import IHasRelations

from plone.formwidget.contenttree import ObjPathSourceBinder
from plone.app.content.interfaces import INameFromTitle

from plone.dexterity.interfaces import IDexterityFTI

from AccessControl import Unauthorized
from Acquisition import aq_base, aq_inner

from Products.CMFCore.PortalContent import PortalContent

from collective.alias import MessageFactory as _
from collective.alias.proxy import AliasProxy

_marker = object()

class IAlias(form.Schema):
    """Schema interface. Note that the alias will also appear to provide the
    schema of the aliased object.
    """
    
    _aliased_object = RelationChoice(
            title=_(u"Aliased object"),
            description=_(u"Choose an object to alias"),
            required=True,
            source=ObjPathSourceBinder(),
        )


class TitleToId(grok.Adapter):
    """Implements title-to-id normalisation for aliases
    """
    
    grok.implements(INameFromTitle)
    grok.context(IAlias)
    
    @property
    def title(self):
        alias = self.context._target
        if alias is None:
            return 'alias'
        
        delegate = INameFromTitle(alias, None)
        if delegate is not None:
            return delegate.title
        
        return alias.Title()


class DelegatingSpecification(ObjectSpecificationDescriptor):
    """A __providedBy__ decorator that returns the interfaces provided by
    the object, plus those of the cached object.
    """
    
    def __get__(self, inst, cls=None):
        
        # We're looking at a class - fall back on default
        if inst is None:
            return getObjectSpecification(cls)
        
        cached_spec = getattr(inst, '_v__providedBy__', None)
        if cached_spec is not None:
            return cached_spec
        
        alias_spec = implementedBy(Alias)
        
        aliased = inst._target
        if aliased is None:
            return alias_spec
        
        spec = inst._v__providedBy__ = alias_spec + aliased.__providedBy__
        return spec


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


class Add(dexterity.AddForm):
    """Override the add form not to depend on the portal_type once the
    object has been created.
    """
    
    grok.name('collective.alias.alias')
    
    def add(self, object):
        
        fti = getUtility(IDexterityFTI, name=self.portal_type)
        container = aq_inner(self.context)
        container = aq_inner(container)
        
        container_fti = container.getTypeInfo()
        
        if not fti.isConstructionAllowed(container):
            raise Unauthorized("Cannot create %s" % self.portal_type)
        
        if container_fti is not None and not container_fti.allowType(self.portal_type):
            raise ValueError("Disallowed subobject type: %s" % self.portal_type)
        
        name = INameChooser(container).chooseName(None, object)
        object.id = name
        
        new_name = container._setObject(name, object)
        
        # XXX: When we move to CMF 2.2, an event handler will take care of this
        new_object = container._getOb(new_name)
        new_object.notifyWorkflowCreated()
        
        immediate_view = fti.immediate_view or 'view'
        self.immediate_view = "%s/%s/%s" % (container.absolute_url(), new_object.id, immediate_view,)


class Alias(PortalContent, Contained):
    grok.implements(IAlias, IHasRelations)
    
    __providedBy__ = DelegatingSpecification()
    _aliased_object = None
    _alias_portal_type = None
    cmf_uid = None
    
    #
    # Delegating methods
    #
    
    # Title and description
    
    def Title(self):
        """Delegated title
        """
        return self.title
    
    @getproperty
    def title(self):
        aliased = self._target
        if aliased is None:
            return ''
        return aliased.Title()
    
    @setproperty
    def title(self, value):
        pass
    
    def Description(self):
        """Delegated description
        """
        aliased = self._target
        if aliased is None:
            return ''
        return aliased.Description()
    
    # Folderishness
    
    @property
    def isPrincipiaFolderish(self):
        aliased = self._target
        if aliased is None:
            return 0
        return aliased.isPrincipaFolderish
    
    # portal_type
    
    @getproperty
    def portal_type(self):
        aliased = self._target
        if aliased is None:
            return self._alias_portal_type
        return aliased.portal_type
    
    @setproperty
    def portal_type(self, value):
        self._alias_portal_type = value
    
    # discussion container
    
    @getproperty
    def talkback(self):
        aliased = self._target
        return aq_base(aliased.talkback).__of__(self) # may legitimately raise an attirbute error
    
    @setproperty
    def talkback(self, value):
        aliased = self._target
        if aliased is None:
            return
        aliased.talkback = value
    
    # Delegate anything else that we can via a __getattr__ hook
    
    def __getattr__(self, name):
        """Delegate attribute access for any attribute not found on the alias
        to the aliased object
        """
        
        if name.startswith('_v_'):
            raise AttributeError(name)
                    
        # This causes all kinds of weirdness...
        if name == '__bobo_traverse__':
            return super(Alias, self).__getattr__(name)
        
        aliased = self._target
        if aliased is None:
            return super(Alias, self).__getattr__(name)
        
        # Don't acquire
        if not hasattr(aq_base(aliased), name):
            return super(Alias, self).__getattr__(name)
        
        # But get an acquisition wrapped object
        aliased_attr = getattr(aliased, name, _marker)
        
        if aliased_attr is _marker:
            return super(Alias, self).__getattr__(name)
        
        return aliased_attr
    
    # Helper to get the object with _v_ caching
    
    @property
    def _target(self):
        aliased = getattr(self, '_v_target', None)
        if aliased is None:
            if self._aliased_object is None or self._aliased_object.isBroken():
                return None
            
            # Get the object and wrap it in an AliasProxy
            aliased = self._v_target = AliasProxy(self._aliased_object.to_object, self)
            
            # Hold this object in the request so that we can wipe the _v_
            # variable when the request is closed. Without this, we get
            # really insane errors with requests that don't have URLs
            # intermittently.
            
            request = getSite().REQUEST
            request._hold(self)
            
        return aliased


@grok.subscribe(IAlias, IObjectModifiedEvent)
def clear_caches(obj, event):
    obj._v_target = None
    obj._v__providedBy__ = None


@grok.subscribe(IEndRequestEvent)
def clear_target_cache(event):
    request = event.request
    if request._held is not None:
        for held in request._held:
            if IAlias.providedBy(held):
                held._v_target = None


@grok.implementer(IAnnotations)
@grok.adapter(IAlias)
def annotations(context):
    """Delegate IAnnotations lookup to work on the aliased object directly.
    """
    aliased = context._target
    if aliased is not None:
        return IAnnotations(aliased, None)
    return None

