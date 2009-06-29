from plone.dexterity.fti import DexterityFTI
from Products.CMFCore.browser.typeinfo import FactoryTypeInformationAddView

from collective.alias.content import IAlias

class AliasFTI(DexterityFTI):
    """An FTI that can borrow actions and method aliases from an aliased
    object
    """
    
    meta_type = "Alias FTI"
    _action_overrides = ('edit',)

    def listActions(self, info=None, object=None):
        """List FTI actions merged with those of the aliased object
        """
        actions = self._actions or ()
        
        if IAlias.providedBy(object):
            aliased = object._target
            if aliased is not None:
                aliased_actions = aliased.getTypeInfo().listActions(info, object)
                current = dict([(a.id, a) for a in actions])
                merged = []
                for a in aliased_actions:
                    if a.id in self._action_overrides and a.id in current:
                        merged.append(current[a.id])
                    else:
                        merged.append(a)
                return merged

        return actions
    
    def queryMethodID(self, alias, default=None, context=None):
        """Look for a method id alias, possibly on the aliased object
        """
        
        if IAlias.providedBy(context):
            aliased = context._target
            if aliased is not None:
                return aliased.getTypeInfo().queryMethodID(alias, default, context=context)
        
        methodTarget = super(AliasFTI, self).queryMethodID(alias, default, context=context)
        
        if not isinstance(methodTarget, basestring):
            # nothing to do, method_id is probably None
            return methodTarget

        if context is None or default == '':
            return methodTarget

        if methodTarget.lower() == "(dynamic view)":
            methodTarget = self.defaultView(context)

        if methodTarget.lower() == "(selected layout)":
            fallback = self.default_view_fallback
            methodTarget = self.getViewMethod(context, check_exists=fallback)

        return methodTarget
    
class FTIAddView(FactoryTypeInformationAddView):
    """Add view for the Dexterity FTI type
    """

    klass = AliasFTI
    description = u'Factory Type Information for content aliases'
