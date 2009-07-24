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

from plone.dexterity.interfaces import IDexterityContent

from plone.folder.ordered import CMFOrderedBTreeFolderBase

from Acquisition import aq_base, aq_inner, aq_parent

from Products.CMFCore.PortalContent import PortalContent
from Products.CMFCore.CMFCatalogAware import CMFCatalogAware

from collective.alias.interfaces import IAlias
from collective.alias.interfaces import IHasAlias

_marker = object()

logger = logging.getLogger('collective.alias')

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


class Alias(CMFCatalogAware, CMFOrderedBTreeFolderBase, PortalContent, Contained):
    grok.implements(IAlias, IDexterityContent, IHasRelations)
    
    __providedBy__ = DelegatingSpecification()
    _alias_portal_type = None
    cmf_uid = None
    
    # to make debugging easier
    isAlias = True
    
    def __init__(self, id=None, **kwargs):
        CMFOrderedBTreeFolderBase.__init__(self, id, **kwargs)
        if id is not None:
            self.id = id
    
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
        return aq_inner(aliased).isPrincipiaFolderish
    
    # def _getOb(self, id, default=_marker):
    #     """ Return the named object from the folder. """
    #     try:
    #         return BTreeFolder2Base._getOb(id, default)
    #     except KeyError, e:
    #         raise AttributeError(e)
    # 
    # def _setOb(self, id, object):
    #     """ Store the named object in the folder. """
    #     # Set __name__ and __parent__ if the object supports it
    #     if ILocation.providedBy(object):
    #         if not IContained.providedBy(object):
    #             alsoProvides(object, IContained)
    #         oldname = getattr(object, '__name__', None)
    #         oldparent = getattr(object, '__parent__', None)
    #         if id is not oldname:
    #             object.__name__ = id
    #         if self is not oldparent:
    #             object.__parent__ = self
    #     BTreeFolder2Base._setOb(id, object)
    #     IOrdering(self).notifyAdded(id)     # notify the ordering adapter
    # 
    # def _delOb(self, id):
    #     """ Remove the named object from the folder. """
    #     # Unset __parent__ and __name__ prior to removing the object.
    #     # Note that there is a slight discrepancy with the Zope 3 behaviour
    #     # here: we do this before the IObjectRemovedEvent is fired. In
    #     # zope.container, IObjectRemovedEvent is fired before the object is
    #     # actually deleted and this information is unset. In Zope2's OFS,
    #     # there's a different IObjectWillBeRemovedEvent that is fired first,
    #     # then the object is removed, and then IObjectRemovedEvent is fired.
    #     try:
    #         obj = self._getOb(id, _marker)
    #         if obj is not _marker:
    #             if IContained.providedBy(obj):
    #                 obj.__parent__ = None
    #                 obj.__name__ = None
    #     except AttributeError:
    #         pass        # No need to fail if we can't set these
    #     super(OrderedBTreeFolderBase, self)._delOb(id)
    #     IOrdering(self).notifyRemoved(id)   # notify the ordering adapter
    # 
    # def objectIds(self, spec=None, ordered=True):
    #     if not ordered:
    #         return super(OrderedBTreeFolderBase, self).objectIds(spec)
    #     ordering = IOrdering(self)
    #     if spec is None:
    #         return ordering.idsInOrder()
    #     else:
    #         ids = super(OrderedBTreeFolderBase, self).objectIds(spec)
    #         idxs = []
    #         for id in ids:
    #             idxs.append((ordering.getObjectPosition(id), id))
    #         return [x[1] for x in sorted(idxs, key=lambda a: a[0])]
    # 
    # def manage_renameObject(self, id, new_id, REQUEST=None):
    #     """ Rename a particular sub-object without changing its position. """
    #     old_position = self.getObjectPosition(id)
    #     result = super(OrderedBTreeFolderBase, self).manage_renameObject(id,
    #         new_id, REQUEST)
    #     if old_position is None:
    #         return result
    #     self.moveObjectToPosition(new_id, old_position, suppress_events=True)
    #     reindex = getattr(self._getOb(new_id), 'reindexObject', None)
    #     if reindex is not None:
    #         reindex(idxs=['getObjPositionInParent'])
    # 
    # def __getitem__(self, key):
    #     # we allow KeyError here (see `_getOb` above)
    #     # XXX: this might shadow the version from OFS.Folder, which gets used
    #     # when inheriting from this class on the archetypes level;  by doing
    #     # so it's likely to break support for webdav...
    #     return super(OrderedBTreeFolderBase, self)._getOb(key)
    
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
    
    # Discussion container - needs special acquisition handling
    
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
    
    # Evil hacks
    
    @property
    def __class__(self):
        """/me whistles and looks to the sky whilst walking slowly backwards,
        hoping no-one noticed what I just did
        """
        aliased = self._target
        if aliased is None:
            return Alias
        else:
            # We need this for super() and friends to work
            
            # XXX: this is mega evil. Cache it at least.
            class Alias_(Alias, aq_base(aliased).__class__):
                pass
            return Alias_
    
    # Delegate anything else that we can via a __getattr__ hook
    
    def __getattr__(self, name):
        """Delegate attribute access for any attribute not found on the alias
        to the aliased object
        """
        
        # Some things we don't delegate:
        #   - the annotations btree (we have an adapter to merge)
        #   - _v_ attributes
        #   - _p_ attributes
        #   - Permissions
        if (
            name == '__annotations__' or
            name.startswith('_v_') or 
            name.startswith('_p_') or 
            name.endswith('_Permission')
        ):
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
    """If the alias is modified, clear the _v_ attribute caches
    """
    obj._v_target = None
    obj._v__providedBy__ = None
