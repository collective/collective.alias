import types

from rwproperty import getproperty, setproperty

from five import grok
from plone.directives import dexterity

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

from z3c.relationfield.interfaces import IHasRelations

from plone.app.content.interfaces import INameFromTitle

from plone.dexterity.interfaces import IDexterityFTI

from AccessControl import Unauthorized
from Acquisition import aq_base, aq_inner, aq_parent

from Products.CMFCore.PortalContent import PortalContent

from collective.alias import MessageFactory as _
from collective.alias.interfaces import IAlias

_marker = object()

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
        
        delegate = INameFromTitle(aq_inner(alias), None)
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
        
        spec = inst._v__providedBy__ = alias_spec + aq_inner(aliased).__providedBy__
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
        return aq_inner(aliased).Title()
    
    @setproperty
    def title(self, value):
        pass
    
    def Description(self):
        """Delegated description
        """
        aliased = self._target
        if aliased is None:
            return ''
        return aq_inner(aliased).Description()
    
    # Folderishness
    
    @property
    def isPrincipiaFolderish(self):
        aliased = self._target
        if aliased is None:
            return 0
        return aq_inner(aliased).isPrincipaFolderish
    
    # portal_type
    
    @getproperty
    def portal_type(self):
        aliased = self._target
        if aliased is None:
            return self._alias_portal_type
        return aq_inner(aliased).portal_type
    
    @setproperty
    def portal_type(self, value):
        self._alias_portal_type = value
    
    # discussion container
    
    @getproperty
    def talkback(self):
        aliased = self._target
        return aq_base(aliased.talkback).__of__(self) # may legitimately raise an attribute error
    
    @setproperty
    def talkback(self, value):
        aliased = self._target
        if aliased is None:
            return
        aq_inner(aliased).talkback = value
    
    @property
    def __class__(self):
        """/me whistles and looks to the sky whilst walking slowly backwards,
        hoping no-one noticed what I just did
        """
        aliased = self._target
        if aliased is None:
            return Alias
        else:
            return aq_base(aliased).__class__
    
    # Delegate anything else that we can via a __getattr__ hook
    
    def __getattr__(self, name):
        """Delegate attribute access for any attribute not found on the alias
        to the aliased object
        """
        
        # Never delegate _v_ attributes. If they're not set on the alias
        # directly, they don't exist.
        if name.startswith('_v_'):
            raise AttributeError(name)
        
        aliased = self._target
        
        # If we don't yet have an alias, then we're out of luck
        if aliased is None:
            return super(Alias, self).__getattr__(name)
        
        # Make sure we get the inner most acquisition chain (i.e. the
        # containment chain)
        aliased = aq_inner(aliased)
        
        # Avoid acquiring anything...
        if not hasattr(aq_base(aliased), name):
            return super(Alias, self).__getattr__(name)
        
        # ... but get an acquisition wrapped object
        aliased_attr = getattr(aliased, name, _marker)
        
        if aliased_attr is _marker:
            return super(Alias, self).__getattr__(name)
        
        # if this is an acquisition wrapped object, re-wrap it in the alias
        if aq_parent(aliased_attr) is aliased:
            aliased_attr = aq_base(aliased_attr).__of__(self)
        
        # if it is a bound method, re-bind it so that im_self is the alias
        if isinstance(aliased_attr, types.MethodType):
            return types.MethodType(aliased_attr.im_func, self, type(self))
        
        return aliased_attr
    
    # Helper to get the object with _v_ caching
    
    @property
    def _target(self):
        aliased = getattr(self, '_v_target', None)
        if aliased is None:
            if self._aliased_object is None or self._aliased_object.isBroken():
                return None
            
            aliased = self._v_target = self._aliased_object.to_object
            
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
        return IAnnotations(aq_inner(aliased), None)
    return None

