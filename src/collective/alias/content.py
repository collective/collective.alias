import logging
import types
import new

from persistent.mapping import PersistentMapping
from rwproperty import getproperty, setproperty

from five import grok

from zope.interface.declarations import implementedBy
from zope.interface.declarations import providedBy
from zope.interface.declarations import getObjectSpecification
from zope.interface.declarations import ObjectSpecificationDescriptor

from zope.component import queryUtility
from zope.annotation.interfaces import IAnnotations

from zope.app.container.contained import Contained

from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from zope.intid.interfaces import IIntIds

from z3c.relationfield.interfaces import IHasRelations
from z3c.relationfield.interfaces import IRelationValue
from z3c.relationfield.relation import RelationValue

from plone.dexterity.interfaces import IDexterityContent
from plone.uuid.interfaces import IAttributeUUID, IUUIDAware

from plone.folder.ordered import CMFOrderedBTreeFolderBase

from plone.app.iterate.interfaces import IIterateAware

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
        provided += providedBy(target) - IHasAlias - IIterateAware
        
        inst._v__providedBy__ = inst._p_mtime, alias_provides, provided
        return provided


class Alias(CMFCatalogAware, CMFOrderedBTreeFolderBase, PortalContent, Contained):
    grok.implements(IAlias, IDexterityContent, IHasRelations, IUUIDAware, IAttributeUUID)
    
    __providedBy__ = DelegatingSpecification()
    _alias_portal_type = None
    _alias_properties = None
    
    cmf_uid = None
    
    _aliasTitle = ''
    _aliasTraversal = False
    
    # to make debugging easier
    isAlias = True
    
    def __init__(self, id=None, **kwargs):
        CMFOrderedBTreeFolderBase.__init__(self, id)
        if id is not None:
            self.id = id
        for k, v in kwargs.items():
            setattr(self, k, v)
        
        # Ensure that the alias gets its own workflow history
        self.workflow_history = PersistentMapping()
     
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
        if self._aliasTitle:
            return self._aliasTitle
        
        aliased = self._target
        if aliased is None:
            return self._aliasTitle
        return aq_inner(aliased).Title()
    
    @setproperty
    def title(self, value):
        self._aliasTitle = value
    
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
    
    # Support for _aliasTraversal
    
    def _getOb(self, id, default=_marker):
        if self._aliasTraversal:
            aliased = self._target
            if aliased is not None:
                obj = aliased._getOb(id, default)
                if obj is default:
                    if default is _marker:
                        raise KeyError(id)
                    return default
                return aq_base(obj).__of__(self)
        return CMFOrderedBTreeFolderBase._getOb(self, id, default)
    
    def objectIds(self, spec=None, ordered=True):
        if self._aliasTraversal:
            aliased = self._target
            if aliased is not None:
                return aliased.objectIds(spec)
        return CMFOrderedBTreeFolderBase.objectIds(self, spec, ordered)
    
    def __getitem__(self, key):
        if self._aliasTraversal:
            aliased = self._target
            if aliased is not None:
                return aliased.__getitem__(key)
        return CMFOrderedBTreeFolderBase.__getitem__(self, key)
    
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
    
    # Hopelessly, Archetypes accesses obj.__annotations__ directly, instead
    # of using an IAnnotations adapter. Delegate to our own adapter, which
    # uses __alias_annotations__ as the "real" dictionary
    
    @getproperty
    def __annotations__(self):
        return IAnnotations(self)
    
    @setproperty
    def __annotations__(self, value):
        pass
    
    # Alias properties until at least one property is modified
    
    @getproperty
    def _properties(self):
        if self._alias_properties is not None:
            return self._alias_properties
        aliased = aq_inner(self._target)
        if aliased is None:
            return super(Alias, self)._properties
        return aliased.properties
    
    @setproperty
    def _properties(self, value):
        self._alias_properties = value
    
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
        
        klass = getattr(self, '_v_class', None)
        if klass is not None:
            return klass
        
        aliased = self._target
        if aliased is None:
            return Alias
        
        self._v_class = klass = new.classobj('Alias', (Alias, aq_base(aliased).__class__), {})
        return klass
    
    # Delegate anything else that we can via a __getattr__ hook
    
    def __getattr__(self, name):
        """Delegate attribute access for any attribute not found on the alias
        to the aliased object
        """
        
        # Some things we don't delegate (but may acquire)
        # 
        #   - the annotations btree (we have an adapter to merge)
        #   - _v_ attributes
        #   - _p_ attributes
        #   - Permissions
        # 

        if (
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
    
    # ensure _aliasTarget is readonly once set
    
    @getproperty
    def _aliasTarget(self):
        return self.__dict__.get('_aliasTarget', None)
    
    @setproperty
    def _aliasTarget(self, value):
        if '_aliasTarget' in self.__dict__:
            raise AttributeError("Cannot set _aliasTarget more than once")
        
        if not IRelationValue.providedBy(value):
            raise AttributeError("_aliasTarget must be an IRelationValue")
        
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
        
        self.__dict__['_aliasTarget'] = value
    
    # Helper to get the object with _v_ caching
    
    @property
    def _target(self):
        aliased = getattr(self, '_v_target', None)
        if aliased is None:
            if self._aliasTarget is None or self._aliasTarget.isBroken():
                return None
            aliased = self._v_target = self._aliasTarget.to_object
            
        return aliased

@grok.subscribe(IAlias, IObjectModifiedEvent)
def clearCaches(obj, event):
    """If the alias is modified, clear the _v_ attribute caches
    """
    obj._v_target = None
    obj._v__providedBy__ = None
