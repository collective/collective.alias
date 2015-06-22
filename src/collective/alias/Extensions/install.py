# -*- coding: utf-8 -*-
from Products.CMFCore import utils as cmfutils
from zope import interface
from zope.component.interface import interfaceToName
from collective.alias.interfaces import IHasAlias
import logging
logger = logging.getLogger("collective.alias uninstall")


def uninstall(portal, reinstall=False):
    if not reinstall:

        # Unprovide all objects from collective.alias.interfaces.IHasAlias
        obj_unprovided = remove_marker_ifaces(portal, IHasAlias)
        logger.info("{0} object unregistred from IHasAlias interface.".format(obj_unprovided))
        # setup_tool = portal.portal_setup
        # setup_tool.runAllImportStepsFromProfile('profile-example.gs:uninstall')


def objs_with_iface(context, iface):
    """Return all objects in the system as found by the nearest portal
    catalog that provides the given interface.  The result will be a generator
    """

    catalog = cmfutils.getToolByName(context, 'portal_catalog')

    for brain in catalog(object_provides=interfaceToName(context, iface)):
        obj = brain.getObject()
        if iface in interface.directlyProvidedBy(obj):
            yield brain.getObject()


def remove_marker_ifaces(context, ifaces):
    """Remove the given interfaces from all objects using a catalog
    query.  context needs to either be the portal or be properly aq wrapped
    to allow for cmf catalog tool lookup.  ifaces can be either a single
    interface or a sequence of interfaces.
    """

    if not isinstance(ifaces, (tuple, list)):
        ifaces = [ifaces]

    count = 0
    for iface in ifaces:
        for obj in objs_with_iface(context, iface):
            count += 1
            provided = interface.directlyProvidedBy(obj)
            interface.directlyProvides(obj, provided - iface)
    return count
