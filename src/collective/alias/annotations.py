from persistent.list import PersistentList

from BTrees.OIBTree import OIBTree
from BTrees.OOBTree import OOBTree

from five import grok

from Acquisition import aq_inner
from UserDict import DictMixin

from zope.annotation.interfaces import IAnnotations

from zope.lifecycleevent.interfaces import IObjectCreatedEvent

from collective.alias.interfaces import IAlias

from plone.folder.default import DefaultOrdering
from plone.contentrules.engine.assignments import KEY as CONTENTRULES_KEY
from plone.portlets.constants import CONTEXT_ASSIGNMENT_KEY

_marker = object()

class AliasAnnotations(grok.Adapter, DictMixin):
    """Annotations on an alias work like regular attribute annotations, except
    that getting items may be delegated to the target. Values are always set
    on the alias' own annotations dictionary, though.
    """
    grok.implements(IAnnotations)
    grok.context(IAlias)
    
    def __init__(self, obj):
        self.obj = obj
        self.target = {}
        
        aliased = self.obj._target
        if aliased is not None:
            self.target = IAnnotations(aq_inner(aliased), {})
        
    def __nonzero__(self):
        return bool(getattr(self.obj, '__alias_annotations__', 0)) or len(self.target)
    
    def get(self, key, default=None):
        value = _marker
        annotations = getattr(self.obj, '__alias_annotations__', _marker)
        if annotations is not _marker:
            value = annotations.get(key, _marker)
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
        annotations = getattr(self.obj, '__alias_annotations__', _marker)
        if annotations is _marker:
            return []
        
        return tuple(set(annotations.keys() + self.target.keys()))
    
    def __setitem__(self, key, value):
        try:
            annotations = self.obj.__alias_annotations__
        except AttributeError:
            annotations = self.obj.__alias_annotations__ = OOBTree()
        annotations[key] = value
    
    def setdefault(self, key, default):
        value = _marker
        annotations = getattr(self.obj, '__alias_annotations__', _marker)
        if annotations is not _marker:
            value = annotations.get(key, _marker)
        if value is _marker:
            self[key] = value = default
        return value
    
    def __delitem__(self, key):
        try:
            annotations = self.obj.__alias_annotations__
        except AttributeError:
            raise KeyError(key)
        del annotations[key]

@grok.subscribe(IAlias, IObjectCreatedEvent)
def initializeAnnotations(obj, event):
    """Ensure that we don't delegate certain annotations by setting them 
    from the beginning.
    """
    annotations = IAnnotations(obj)
    annotations.setdefault(DefaultOrdering.ORDER_KEY, PersistentList())
    annotations.setdefault(DefaultOrdering.POS_KEY, OIBTree())
    annotations.setdefault(CONTENTRULES_KEY, None)
    annotations.setdefault(CONTEXT_ASSIGNMENT_KEY, OOBTree())
