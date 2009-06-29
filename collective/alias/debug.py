from five import grok
from zope.interface import Interface

class DebugView(grok.View):
    grok.name('debug')
    grok.context(Interface)
    
    def render(self):
        import pdb; pdb.set_trace( )
        return ''