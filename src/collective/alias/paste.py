from five import grok

from Acquisition import aq_inner

from OFS.CopySupport import _cb_decode
from OFS.interfaces import IObjectManager

import OFS.Moniker

from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent

from zope.component import getUtility
from z3c.relationfield import RelationValue
from zope.intid.interfaces import IIntIds

from plone.dexterity.utils import createContent

# XXX: Should move to zope.container in the future
from zope.app.container.interfaces import INameChooser

def pasteAsAlias(context, cb_copy_data=None, request=None):
    """Paste the clipboard contents as an alias. Either pass the data, or a
    valid request with the __cp key.
    """

    cp = None

    if cb_copy_data is not None:
        cp = cb_copy_data
    elif request and request.has_key('__cp'):
        cp = request['__cp']
    else:
        cp = None

    if cp is None:
        raise ValueError("No clipboard data")

    try:
        cp = _cb_decode(cp)
    except:
        raise ValueError("Can't decode clipboard: %r" % cp)

    oblist = []
    app = context.getPhysicalRoot()

    failed = []
    success = []

    for mdata in cp[1]:
        m = OFS.Moniker.loadMoniker(mdata)
        try:
            ob = m.bind(app)
        except:
            raise ValueError("Objects not found in %s" % app)
        oblist.append(ob)

    intids = getUtility(IIntIds)

    for ob in oblist:
        relation = RelationValue(intids.getId(ob))
        alias = createContent('collective.alias', _aliasTarget=relation)

        notify(ObjectCreatedEvent(alias))

        name = INameChooser(context).chooseName(ob.getId(), alias)
        alias.id = name

        new_name = context._setObject(name, alias)

        # XXX: When we move to CMF 2.2, an event handler will take care of this
        new_object = context._getOb(new_name)
        new_object.notifyWorkflowCreated()

    return ' '.join(success) + ' '.join(failed)

class PasteAsAlias(grok.View):
    """View used as an action for pasting the clipboard contents as aliases
    """
    grok.context(IObjectManager)
    grok.name('paste-alias')
    grok.require('collective.alias.AddAlias')

    def update(self):
        message = pasteAsAlias(context=aq_inner(self.context), request=self.request)
        self.request.response.redirect(self.context.absolute_url())

    def render(self):
        return ''

