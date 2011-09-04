from plone.uuid.handlers import addAttributeUUID

from zc.relation.interfaces import ICatalog
from zope.component import getUtility
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent

from Products.CMFCore.utils import getToolByName

from collective.alias.interfaces import IAlias


def add_uuid(context):
    rcatalog = getUtility(ICatalog)
    # Clear the relation catalog to fix issues with interfaces that don't exist anymore.
    # This actually fixes the from_interfaces_flattened and to_interfaces_flattened indexes.
    # The ObjectModifiedEvent takes care of reindexing the relations only for aliases.
    # /!\ If you have other dexterity content types with relations, you have to
    # write a script that notify an ObjectModifiedEvent for each instance to
    # reindex the relations.
    rcatalog.clear()

    catalog = getToolByName(context, 'portal_catalog')
    brains = catalog.searchResults(object_provides=IAlias.__identifier__)
    for brain in brains:
        obj = brain.getObject()
        addAttributeUUID(obj, None)
        obj.reindexObject(idxs=['object_provides', 'UID'])
        try:
            for comment_id in obj.talkback.objectIds():
                obj.unrestrictedTraverse(('talkback', comment_id)).unindexObject()
        except AttributeError: # no talkback
            pass
        notify(ObjectModifiedEvent(obj))


def upgrade_actions(context):
    context.runImportStepFromProfile('profile-collective.alias:default',
                                     'actions')
