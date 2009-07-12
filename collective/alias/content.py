import logging
import types

from rwproperty import getproperty, setproperty

from five import grok
from plone.directives import dexterity

from zope.interface import alsoProvides
from zope.interface import noLongerProvides

from zope.interface.declarations import implementedBy
from zope.interface.declarations import providedBy
from zope.interface.declarations import getObjectSpecification
from zope.interface.declarations import ObjectSpecificationDescriptor

from zope.component import getUtility
from zope.component import queryUtility

from zope.event import notify

from zope.annotation.interfaces import IAnnotations

from zope.lifecycleevent.interfaces import IObjectCreatedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.lifecycleevent import ObjectModifiedEvent

# XXX: Should move to zope.container in the future
from zope.app.container.interfaces import IObjectAddedEvent
from zope.app.container.interfaces import IObjectRemovedEvent

from zope.app.container.interfaces import INameChooser
from zope.app.container.contained import Contained

from zope.intid.interfaces import IIntIds
from zc.relation.interfaces import ICatalog

from z3c.relationfield.interfaces import IHasRelations
from z3c.relationfield.relation import RelationValue

from plone.app.content.interfaces import INameFromTitle

from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.interfaces import IDexterityContent

from AccessControl import Unauthorized
from Acquisition import aq_base, aq_inner, aq_parent

from Products.CMFCore.PortalContent import PortalContent

from collective.alias import MessageFactory as _

from collective.alias.interfaces import IAlias
from collective.alias.interfaces import IHasAlias
from collective.alias.interfaces import IAliasInformation

_marker = object()

logger = logging.getLogger('collective.alias')

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
        
        # Find the cached value.
        cache = getattr(inst, '_v__providedBy__', None)
        
        # Find the data we need to know if our cache needs to be invalidated
        provided = alias_provides = getattr(inst, '__provides__', None)
        
        # See if we have a valid cache, and if so return it
        if cache is not None:
            cached_mtime, cached_provides, cached_provided = cache
            
            if (
                inst._p_mtime == cached_mtime and 
                alias_provides is cached_provides
            ):
                return cached_provided
        
        # If the instance doesn't have a __provides__ attribute, get the
        # interfaces implied by the class as a starting point.
        if provided is None:
            assert cls == Alias # XXX: remove
            provided = implementedBy(cls)
        
        # Add the interfaces provided by the target 
        target = aq_base(inst._target)
        if target is None:
            return provided # don't cache yet!
        
        # Add the interfaces provided by the target, but take away
        # IHasAlias if set
        provided += providedBy(target) - IHasAlias
        
        inst._v__providedBy__ = inst._p_mtime, alias_provides, provided
        return provided


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
    grok.implements(IAlias, IDexterityContent, IHasRelations)
    
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
        if not hasattr(aq_base(aliased), 'talkback'):
            raise AttributeError('talkback')
        # may legitimately raise an attribute error
        return aq_base(aliased.talkback).__of__(self)
    
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
            
        return aliased


@grok.implementer(IAnnotations)
@grok.adapter(IAlias)
def annotations(context):
    """Delegate IAnnotations lookup to work on the aliased object directly.
    """
    aliased = context._target
    if aliased is not None:
        return IAnnotations(aq_inner(aliased), None)
    return None


@grok.subscribe(IHasAlias, IObjectModifiedEvent)
@grok.subscribe(IAlias, IObjectModifiedEvent)
def clearCaches(obj, event):
    obj._v_target = None
    obj._v__providedBy__ = None


@grok.subscribe(IAlias, IObjectCreatedEvent)
def resolveTransitiveAlias(alias, event):
    """When an alias is created, check to see if it is pointing to another
    alias and resolve the reference to the underlying target.
    """
        
    target = aq_inner(alias._target)
    if target is None:
        return
    
    counter = 0
    
    while IAlias.providedBy(target) and counter < 1000: # avoid infinite loop
        target = aq_inner(target._target)
        counter += 1
    
    if counter > 0:
        intids = queryUtility(IIntIds)
        
        if intids is None:
            raise LookupError("Cannot find intid utility")
        
        to_id = intids.getId(target) # may raise KeyError
        alias._aliased_object = RelationValue(to_id)
        alias._v_target = None

@grok.subscribe(IHasAlias, IObjectModifiedEvent)
def rebroadcastModifiedEvent(obj, event):
    """When an object with an alias is modified, consider the alias modified
    as well. This will e.g. 
    """
    info = IAliasInformation(obj, None)
    if info is not None:
        for alias in info.findAliases():
            new_event = ObjectModifiedEvent(alias, *event.descriptions)
            notify(new_event)


# Manage the IHasAlias marker

@grok.subscribe(IAlias, IObjectAddedEvent)
def markTargetOnAdd(alias, event):
    """When the alias is added, mark the target with IHasAlias
    """
    
    target = aq_inner(alias._target)
    if target is not None and not IHasAlias.providedBy(target):
        alsoProvides(target, IHasAlias)


@grok.subscribe(IAlias, IObjectRemovedEvent)
def unmarkTargetOnRemove(alias, event):
    """When the alias is created, 
    """
    target = aq_inner(alias._target)
    if target is not None and IHasAlias.providedBy(target):
        
        intids = queryUtility(IIntIds)
        catalog = queryUtility(ICatalog)
        
        if intids is not None and catalog is not None:
            
            try:
                to_id = intids.getId(target)
            except KeyError:
                logging.error("Alias target %s does not have an intid" % target)
                return
            
            alias_base = aq_base(alias)
            
            for rel in catalog.findRelations({
                'to_id': to_id,
                'from_interfaces_flattened': IAlias,
                'from_attribute': '_aliased_object',
            }):
                # abort if there is another alias
                if alias_base is not rel.from_object:
                    return
        
        noLongerProvides(target, IHasAlias)
