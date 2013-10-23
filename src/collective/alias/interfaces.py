from zope.interface import Interface
from zope import schema

from plone.formwidget.contenttree import ObjPathSourceBinder
from plone.supermodel import model
from z3c.relationfield.schema import RelationChoice

from collective.alias import MessageFactory as _


class IAlias(model.Schema):
    """Schema interface. Note that the alias will also appear to provide the
    schema of the aliased object.
    """
    
    _aliasTarget = RelationChoice(
            title=_(u"Aliased object"),
            description=_(u"Choose an object to alias"),
            required=True,
            source=ObjPathSourceBinder(),
        )
    
    _aliasTitle = schema.TextLine(
            title=_(u"Title override"),
            description=_(u"If you want your alias to have a different title "
                           "than the aliased object, enter a title here."),
            required=False,
        )
    
    _aliasTraversal = schema.Bool(
            title=_(u"Allow traversal"),
            description=_(u"If selected, children of the aliased object will "
                           "appear as children of the alias. Note that they "
                           "will not be indexed in the catalog, and probably "
                           "won't show up in folder listings. This option "
                           "may be useful for e.g. Collections, where some "
                           "information is stored in child objects."),
            required=True,
            default=False,
        )


class IAliasSettings(model.Schema):
    """Configuration settings used in registry.xml
    """
    
    traversalTypes = schema.List(
            title=_(u"Traversal types"),
            description=_(u"List of types which by default allow traversal"),
            required=True,
            default=[],
            value_type=schema.Choice(vocabulary="collective.alias.PortalTypes"),
        )
    
    aliasActions = schema.Set(
            title=_(u"Alias actions"),
            description=_(u"Ids of actions that are allowed on aliases"),
            required=True,
            default=set(),
            value_type=schema.ASCIILine(),
        )


class IHasAlias(Interface):
    """Marker interface set on content that has an alias somewhere.
    """


class IAliasInformation(Interface):
    """Adapt an object that has an alias to this interface to get alias
    information.
    """
    
    def findAliases(interface=IAlias):
        """Return a generator of objects representing aliases of the
        context. The alias will provide the interface specified in
        'interface'.
        """
    
    def findAliasIds(interface=IAlias):
        """Return a generator of alias intids representing aliases of the
        context. The alias will provide the interface specified in
        'interface'.
        """
