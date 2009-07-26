from persistent.list import PersistentList
from BTrees.OIBTree import OIBTree

from five import grok

from Acquisition import aq_inner

from zope.annotation.interfaces import IAnnotations
from zope.annotation.attribute import AttributeAnnotations

from zope.lifecycleevent.interfaces import IObjectCreatedEvent

from collective.alias.interfaces import IAlias

from plone.folder.default import DefaultOrdering
from plone.contentrules.engine.assignments import KEY as CONTENTRULES_KEY

_marker = object()

class AliasAnnotations(grok.Adapter, AttributeAnnotations):
    """Annotations on an alias work like regular attribute annotations, except
    that getting items may be delegated to the target. Values are always set
    on the alias' own annotations dictionary, though.
    """
    grok.context(IAlias)
    
    def __init__(self, obj):
        self.obj = obj
        self.target = {}
        
        aliased = self.obj._target
        if aliased is not None:
            self.target = IAnnotations(aq_inner(aliased), {})
        
    def __nonzero__(self):
        return bool(getattr(self.obj, '__annotations__', 0)) or len(self.target)
    
    def setdefault(self, key, default):
        value = super(AliasAnnotations, self).get(key, _marker)
        if value is _marker:
            self[key] = value = default
        return value
    
    def get(self, key, default=None):
        value = super(AliasAnnotations, self).get(key, _marker)
        if value is _marker:
            value = self.target.get(key, _marker)
        if value is _marker:
            return default
        return value

    def __getitem__(self, key):
        value = self.get(key, _marker)
        if value is _marker:
            raise KeyError(key)
        return value

    def keys(self):
        return tuple(set(super(AliasAnnotations, self).keys() + self.target.keys()))

@grok.subscribe(IAlias, IObjectCreatedEvent)
def initializeAnnotations(obj, event):
    """Ensure that we don't delegate certain annotations by setting them 
    from the beginning.
    """
    annotations = IAnnotations(obj)
    annotations.setdefault(DefaultOrdering.ORDER_KEY, PersistentList())
    annotations.setdefault(DefaultOrdering.POS_KEY, OIBTree())
    annotations.setdefault(CONTENTRULES_KEY, None)