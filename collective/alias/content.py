from five import grok
from plone.directives import form, dexterity

from Acquisition import aq_base

from Products.CMFCore.PortalContent import PortalContent
from zope.app.container.contained import Contained

from z3c.relationfield.schema import RelationChoice
from z3c.relationfield.interfaces import IHasRelations

from plone.formwidget.contenttree import ObjPathSourceBinder
from plone.app.content.interfaces import INameFromTitle

from collective.alias import MessageFactory as _

from zope.interface.declarations import implementedBy
from zope.interface.declarations import getObjectSpecification
from zope.interface.declarations import ObjectSpecificationDescriptor

from rwproperty import getproperty, setproperty

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
            return 'broken-alias'
        return alias.Title()

class DelegatingSpecification(ObjectSpecificationDescriptor):
    """A __providedBy__ decorator that returns the interfaces provided by
    the object, plus those of the cached object.
    """
    
    def __get__(self, inst, cls=None):
        
        # We're looking at a class - fall back on default
        if inst is None:
            return getObjectSpecification(cls)
        
        alias_spec = implementedBy(Alias)
        
        aliased = inst._target
        if aliased is None:
            return alias_spec
        
        return alias_spec + aliased.__providedBy__

class Edit(dexterity.EditForm):
    grok.context(IAlias)
    grok.name('edit')

class Alias(PortalContent, Contained):
    grok.implements(IAlias, IHasRelations)
    
    __providedBy__ = DelegatingSpecification()
    _aliased_object = None
    cmf_uid = None
    
    # Make a few methods and properties that we've inherited delegate to 
    # the aliased object
    
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
    
    @property
    def isPrincipiaFolderish(self):
        aliased = self._target
        if aliased is None:
            return 0
        return aliased.isPrincipaFolderish
    
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
        aliased_attr = getattr(aliased, name, None)
        
        if aliased_attr is None:
            return super(Alias, self).__getattr__(name)
        
        return aliased_attr

    # Helper to get the object with _v_ caching
    @property
    def _target(self):
        aliased = getattr(self, '_v_aliased_object', None)
        if aliased is None:
            if self._aliased_object is None or self._aliased_object.isBroken():
                return None
            aliased = self._v_aliased_object = self._aliased_object.to_object
        return aliased