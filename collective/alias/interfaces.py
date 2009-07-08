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