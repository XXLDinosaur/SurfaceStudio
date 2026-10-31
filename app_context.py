"""Explicit mutable application state. Services are wired once at startup."""
import threading

class ApplicationContext:
    FIELDS=frozenset('DATA CACHE DEFAULT_ROOT PORT TOKEN LOCK THUMB_LOCK CONFIG STATE INDEX SCANNING SCAN_ERROR ASSETS BRIDGE'.split())
    def __init__(self):
        self.LOCK=threading.RLock()
        self.THUMB_LOCK=threading.Semaphore(4)
        self.CONFIG={};self.STATE={};self.INDEX={};self.ASSETS={}
        self.SCANNING=False;self.SCAN_ERROR=None
        self.services={}
    def __getattr__(self,name):
        services=self.__dict__.get('services',{})
        if name in services:return services[name]
        raise AttributeError(name)
    def snapshot_for_test(self):
        import copy
        return copy.copy(self)

def expose_legacy_state(module,context):
    """Compatibility for desktop/tests; state has one owner, never a copied dict."""
    import types
    class StateModule(types.ModuleType):
        def __getattr__(self,name):
            if name in context.FIELDS:return getattr(context,name)
            raise AttributeError(name)
        def __setattr__(self,name,value):
            if name in context.FIELDS:setattr(context,name,value)
            else:super().__setattr__(name,value)
        def __delattr__(self,name):
            if name in context.FIELDS:delattr(context,name)
            else:super().__delattr__(name)
    module.__class__=StateModule

