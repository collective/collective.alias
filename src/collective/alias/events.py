import logging

from five import grok

from zope.interface import alsoProvides
from zope.interface import noLongerProvides

from zope.component import queryUtility

from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.lifecycleevent.interfaces import IObjectCopiedEvent
from zope.lifecycleevent.interfaces import IObjectCreatedEvent

from zope.lifecycleevent import ObjectModifiedEvent

# XXX: Should move to zope.container in the future
from zope.app.container.interfaces import IObjectAddedEvent
from zope.app.container.interfaces import IObjectRemovedEvent

from OFS.interfaces import IObjectWillBeRemovedEvent

from zope.intid.interfaces import IIntIds
from zc.relation.interfaces import ICatalog

from plone.registry.interfaces import IRegistry

from Acquisition import aq_base, aq_inner, aq_parent

from collective.alias.interfaces import IAlias
from collective.alias.interfaces import IHasAlias
from collective.alias.interfaces import IAliasInformation
from collective.alias.interfaces import IAliasSettings

from zope.event import notify

logger = logging.getLogger('collective.alias')

# Event delegation

@grok.subscribe(IHasAlias, IObjectModifiedEvent)
def rebroadcastModifiedEvent(obj, event):
    """When an object with an alias is modified, consider the alias modified
    as well. This will e.g. 
    """
    info = IAliasInformation(obj, None)
    if info is not None:
        for alias in info.findAliases():
            new_event = ObjectModifiedEvent(alias, *event.descriptions)
            notify(new_event)

# Set the _aliasTraversal flag based on type defaults

@grok.subscribe(IAlias, IObjectCreatedEvent)
def setAliasTraversal(alias, event):
    """When the alias is create, set the _aliasTraversal attribute according
    to the settings in the registry.
    """
    
    registry = queryUtility(IRegistry)
    if registry is None:
        return
    
    try:
        settings = registry.forInterface(IAliasSettings)
    except KeyError:
        return
    
    if alias.portal_type in settings.traversalTypes:
        alias._aliasTraversal = True

# Manage the IHasAlias marker

@grok.subscribe(IAlias, IObjectAddedEvent)
def markTargetOnAdd(alias, event):
    """When the alias is added, mark the target with IHasAlias
    """
    
    target = aq_inner(alias._target)
    if target is not None and not IHasAlias.providedBy(target):
        alsoProvides(target, IHasAlias)


@grok.subscribe(IAlias, IObjectRemovedEvent)
def unmarkTargetOnRemove(alias, event):
    """When the alias is created, 
    """
    target = aq_inner(alias._target)
    if target is not None and IHasAlias.providedBy(target):
        
        intids = queryUtility(IIntIds)
        catalog = queryUtility(ICatalog)
        
        if intids is not None and catalog is not None:
            
            try:
                to_id = intids.getId(target)
            except KeyError:
                logger.error("Alias target %s does not have an intid" % target)
                return
            
            alias_base = aq_base(alias)
            
            for rel in catalog.findRelations({
                'to_id': to_id,
                'from_interfaces_flattened': IAlias,
                'from_attribute': '_aliasTarget',
            }):
                # abort if there is another alias
                if alias_base is not rel.from_object:
                    return
        
        noLongerProvides(target, IHasAlias)


@grok.subscribe(IHasAlias, IObjectCopiedEvent)
def unmarkCopy(obj, event):
    """If an object is copied, remove the marker. At this point, we don't
    have an intid yet, so we can't add an alias anyway. It's possible an
    alias will be added later, e.g. in response to an IObjectAddedEvent,
    which is fine: the corresponding IObjectAddedEvent on the IAlias will
    then re-add the marker.
    """
    noLongerProvides(event.object, IHasAlias)

# Handle deletion

@grok.subscribe(IHasAlias, IObjectWillBeRemovedEvent)
def removeAliasOnDelete(obj, event):
    """When an object with an alias is removed, remove all aliases as well.
    """
    info = IAliasInformation(event.object, None)
    if info is not None:
        
        # take off the marker interface now so that the handler for
        # (IAlias, IObjectRemovedEvent) doesn't try to go in circles
        noLongerProvides(event.object, IHasAlias)
        
        for alias in info.findAliases():
            parent = aq_parent(aq_inner(alias))
            parent._delObject(alias.getId())