import dlvhex
import hexlite.ast.shallowparser as shp
from hexlite.ast import alist as alist
import hexlite
import logging

class ListProcessor:
	def __init__(self):
		pass

	def evaluate(self, expression):
		#logging.warning("ListProcessor evaluating %s", expression)
		parsed = shp.parseTerm(expression)
		#logging.warning("ListProcessor parsed %s", parsed)
		if len(parsed) != 2 or not parsed[1].match(('(',None,')')):
			raise ValueError("ListProcessor commands are always of the form 'cmd(arguments)', encountered %s" % expression)
		cmd = parsed[0]
		args = parsed[1]
		handlers = {
			'at': self.handleAt,
			'len': self.handleLen,
			'pop_front': self.handlePopFront,
			'append': self.handleAppend,
		}
		if cmd not in handlers:
			raise ValueError("ListProcessor commands are one of %s, encountered %s" % (handlers.keys(), cmd))
		ret = handlers[cmd](args)
		#logging.warning("ListProcessor returned %s for input %s", shp.shallowprint(ret), expression)
		return ret

	def getListArg(self, args, idx):
		if len(args) <= idx:
			raise ValueError("ListProcessor expects at least %d arguments, got %s" % (idx+1, shp.shallowprint(args)))
		l = args[idx]
		if len(l) < 1 or l[0] != 'c':
			raise ValueError("ListProcessor expects list of form c(...) or c [empty list] instead of %s" % shp.shallowprint(l))
		if len(l) == 1:
			# empty list
			logging.debug("parsed %s into the empty list", repr(l))
			return []
		if not l[1].match(('(',None,')')):
			raise ValueError("ListProcessor expects list of form c(...) or c [empty list] instead of %s" % shp.shallowprint(l))
		ret = list(l[1])
		logging.debug("parsed %s into list %s", shp.shallowprint(l), repr(ret))
		return ret

	def getNonlistArg(self, args, idx):
		if len(args) <= idx:
			raise ValueError("ListProcessor expects at least %d arguments, got %s" % (idx+1, shp.shallowprint(args)))
		i = args[idx]
		if len(i) == 1:
			i = i[0]
		logging.debug("parsed %s into non-list %s", shp.shallowprint(args[idx]), repr(i))
		return i

	def createList(self, contents):
		ret = ['c', alist(contents, left='(', sep=',', right=')')]
		logging.debug("createlist created %s", shp.shallowprint(ret))
		return ret

	def handleAt(self, args):
		'''
		at(<list>,<index>) = the element at <list>[<index>]
		'''
		l = self.getListArg(args, 0)
		i = int(self.getNonlistArg(args, 1))
		if i >= len(l):
			# no result because operation is meaningless
			logging.info("attempt to address element %d of list %s of length %d", i, l, len(l))
			return None
		selected = l[i]
		#logging.warning("ListProcessor at got selected arg %d = %s", i, selected)
		if isinstance(selected, list) and len(selected) == 1:
			ret = selected[0]
			#if ret[0] == '"' and ret[-1] == '"':
			#	ret = ret[1:-1]
		else:
			ret = selected
		#logging.warning("ListProcessor at(...) returns %s", ret)
		return ret

	def handleLen(self, args):
		'''
		len(<list>) = the length of the list
		'''
		l = self.getListArg(args, 0)
		ret = len(l)
		logging.debug("ListProcessor len(...) returns %d for list %s", ret, shp.shallowprint(l))
		return ret

	def handlePopFront(self, args):
		'''
		pop_front(<list>) = the list <list>[1:]
		'''
		l = self.getListArg(args, 0)
		logging.debug("ListProcessor pop_front() got list %s", l)
		if len(l) == 0:
			# empty list -> pop_front does not even return an empty list but None
			return None
		return self.createList(l[1:])

	def handleAppend(self, args):
		'''
		append(<list>,<newitem>) = the list <list> + [<newitem>]
		'''
		l = self.getListArg(args, 0)
		i = self.getNonlistArg(args, 1)
		newcontent = list(l) + [i]
		logging.debug("ListProcessor appends %s to %s", repr(i), repr(l))
		return self.createList(newcontent)

lp = ListProcessor()

def list0(expr):
	expr = expr.value().strip('"')
	result = lp.evaluate(expr)
	if result == True:
		dlvhex.output( () )
	elif result != False:
		logging.warning("expression %s yielded non-boolean result %s but was used in boolean context list0[<expr>]()", expr, result)

def list1(expr):
	expr = expr.value().strip('"')
	result = lp.evaluate(expr)
	if result is None:
		# that is fine, it means the operation cannot be done, e.g., at([1,2],4) or pop_front([])
		pass
	elif result in [True,False] or isinstance(result,int):
		#logging.debug("list1 for %s storing integer %d", expr, int(result))
		dlvhex.output( (dlvhex.storeInteger(int(result)),) )
	elif isinstance(result,str):
		if result[0] == '"':
			dlvhex.output( (dlvhex.storeString(result[1:-1]),) )
		else:
			dlvhex.output( (dlvhex.storeConstant(result),) )
	elif isinstance(result,alist) or isinstance(result,list):
		t = shp.shallowprint(result, unaryTupleFinalComma=True)
		pi = dlvhex.storeParseable(t)
		#logging.warning("printing result for storeParseable: %s yielded %s", t, repr(pi.symlit.sym))
		dlvhex.output( (pi,) )
	else:
		logging.warning("expression %s yielded result %s that cannot be converted to HEX ID", expr, repr(result))

def register():
	dlvhex.addAtom("list0", (dlvhex.CONSTANT,), 0)
	dlvhex.addAtom("list1", (dlvhex.CONSTANT,), 1)


# vim:noexpandtab:nolist:
