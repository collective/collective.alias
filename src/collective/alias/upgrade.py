from plone.uuid.handlers import addAttributeUUID

from zc.relation.interfaces import ICatalog
from zope.component import getUtility
from z3c.relationfield.event import updateRelations
from z3c.relationfield.interfaces import IHasRelations

from Products.CMFCore.utils import getToolByName

from collective.alias.interfaces import IAlias


def reindex_relations(context):
    rcatalog = getUtility(ICatalog)
    # Clear the relation catalog to fix issues with interfaces that don't exist anymore.
    # This actually fixes the from_interfaces_flattened and to_interfaces_flattened indexes.
    rcatalog.clear()

    catalog = getToolByName(context, 'portal_catalog')
    brains = catalog.searchResults(object_provides=IHasRelations.__identifier__)
    for brain in brains:
        obj = brain.getObject()
        updateRelations(obj, None)


def add_uuid(context):
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


def upgrade_actions(context):
    context.runImportStepFromProfile('profile-collective.alias:default',
                                     'actions')
