from five import grok

from Acquisition import aq_inner

from zope.annotation.interfaces import IAnnotations
from collective.alias.interfaces import IAlias

@grok.implementer(IAnnotations)
@grok.adapter(IAlias)
def annotations(context):
    """Delegate IAnnotations lookup to work on the aliased object directly.
    """
    aliased = context._target
    if aliased is not None:
        return IAnnotations(aq_inner(aliased), None)
    return None