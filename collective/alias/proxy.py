from zope.interface import implements
from zope.proxy import ProxyBase
from collective.alias.interfaces import IAliasProxy

_marker = object()

class AliasProxy(ProxyBase):
    """This is an almost-transparent proxy that will be wrapped around
    the aliased object in order to allow methods to be executed that
    treat the alias object as 'self'.
    """
    implements(IAliasProxy)
    
    __slots__ = ('_alias',)
    
    def __new__(self, ob, alias):
        return ProxyBase.__new__(self, ob)
    
    def __init__(self, ob, alias):
        ProxyBase.__init__(self, ob)
        self._alias = alias
    
    def __getattribute__(self, name):
        if name != '__class__':
            alias = ProxyBase.__getattribute__(self, '_alias')
            try:
                return object.__getattribute__(alias, name)
            except AttributeError:
                pass
        return ProxyBase.__getattribute__(self, name)
