import logging

from zope.component import queryUtility

from zope.intid.interfaces import IIntIds
from zc.relation.interfaces import ICatalog

from five import grok
from collective.alias.interfaces import IAlias, IAliasInformation, IHasAlias

logger = logging.getLogger('collective.alias')

class AliasInformation(grok.Adapter):
    """Default alias information
    """
    
    grok.implements(IAliasInformation)
    grok.context(IHasAlias)
    
    def findAliases(self, interface=IAlias):
        
        intids = queryUtility(IIntIds)
        for intid in self.findAliasIds(interface):
            
            # Note: from_object gets a non-aq-wrapped object, so we look it
            # up like this
    
            try:
                yield intids.getObject(intid)
            except KeyError:
                logger.alias('Invalid alias relationship: from_id %s does not exist' % intid)
    
    def findAliasIds(self, interface=IAlias):
        
        catalog = queryUtility(ICatalog)
        if catalog is None:
            raise LookupError("Cannot find relationship catalog utility")
        
        intids = queryUtility(IIntIds)
        if intids is None:
            raise LookupError("Cannot find intid utility")
        
        to_id = intids.getId(self.context)
        
        for rel in catalog.findRelations({
            'to_id': to_id,
            'from_interfaces_flattened': interface,
            'from_attribute': '_aliasTarget',
        }):
            
            yield rel.from_id
