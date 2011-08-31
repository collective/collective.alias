from plone.uuid.handlers import addAttributeUUID
from Products.CMFCore.utils import getToolByName
from collective.alias.interfaces import IAlias

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