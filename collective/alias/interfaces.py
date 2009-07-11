from zope.interface import Interface
from plone.directives import form

from z3c.relationfield.schema import RelationChoice
from plone.formwidget.contenttree import ObjPathSourceBinder

from collective.alias import MessageFactory as _

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

class IHasAlias(Interface):
    """Marker interface set on content that has an alias somewhere.
    """

class IAliasInformation(Interface):
    """Adapt an object that has an alias to this interface to get alias
    information.
    """
    
    def find_aliases(interface=IAlias):
        """Return a generator of objects representing aliases of the
        context. The target will provide the interface specified in
        'Interface'.
        """