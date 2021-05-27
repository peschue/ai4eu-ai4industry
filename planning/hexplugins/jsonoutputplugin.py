import dlvhex
from hexlite.modelcallback import JSONModelCallback

def register():
	dlvhex.registerModelCallbackClass(JSONModelCallback)
