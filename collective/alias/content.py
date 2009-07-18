import logging
import types

from rwproperty import getproperty, setproperty

from five import grok

from zope.interface.declarations import implementedBy
from zope.interface.declarations import providedBy
from zope.interface.declarations import getObjectSpecification
from zope.interface.declarations import ObjectSpecificationDescriptor

from zope.component import queryUtility

from zope.app.container.contained import Contained

from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from zope.intid.interfaces import IIntIds

from z3c.relationfield.interfaces import IHasRelations
from z3c.relationfield.interfaces import IRelationValue
from z3c.relationfield.relation import RelationValue

from plone.app.content.interfaces import INameFromTitle
from plone.dexterity.interfaces import IDexterityContent

from Acquisition import aq_base, aq_inner, aq_parent
from Products.CMFCore.PortalContent import PortalContent

from collective.alias.interfaces import IAlias
from collective.alias.interfaces import IHasAlias

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


class Alias(PortalContent, Contained):
    grok.implements(IAlias, IDexterityContent, IHasRelations)
    
    __providedBy__ = DelegatingSpecification()
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
    
    # ensure _aliased_object is readonly once set
    
    @getproperty
    def _aliased_object(self):
        return self.__dict__.get('_aliased_object', None)
    
    @setproperty
    def _aliased_object(self, value):
        if '_aliased_object' in self.__dict__:
            raise AttributeError("Cannot set _aliased_object more than once")
        
        if not IRelationValue.providedBy(value):
            raise AttributeError("_aliased_object must be an IRelationField")
        
        counter = 0
        
        target = value.to_object
        while IAlias.providedBy(target) and counter < 1000: # avoid infinite loop
            target = aq_inner(target._target)
            counter += 1
        
        if counter > 0:
            intids = queryUtility(IIntIds)
            
            if intids is None:
                raise LookupError("Cannot find intid utility")
            
            to_id = intids.getId(target)
            value = RelationValue(to_id)
        
        self.__dict__['_aliased_object'] = value
    
    # Helper to get the object with _v_ caching
    
    @property
    def _target(self):
        aliased = getattr(self, '_v_target', None)
        if aliased is None:
            if self._aliased_object is None or self._aliased_object.isBroken():
                return None
            aliased = self._v_target = self._aliased_object.to_object
            
        return aliased


@grok.subscribe(IAlias, IObjectModifiedEvent)
def clearCaches(obj, event):
    obj._v_target = None
    obj._v__providedBy__ = None