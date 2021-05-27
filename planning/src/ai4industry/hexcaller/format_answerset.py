#!/usr/bin/env python3

import json, sys, logging, collections, re, itertools
import pandas as pd

class PlanFormatter:
  def __init__(self):
    pass

  def msg(self, s):
    logging.info('MSG '+s)

  def shorten_terms(self, s):
    #return s.replace('Module', 'Md').replace('ConveyorBelt','CB').replace('Unit','U').replace('Stackingmagazin','Mag').replace('_','').replace('Blue','B').replace('Red','R').replace('Feeding','Fd').replace('Transfer','Xf')
    return s

  def shorten_uri(self, uri):
    #logging.warning("call to shorten_uri with %s", repr(uri))
    if uri[0] == '"':
      uri = uri[1:-1]
    if '#' in uri:
      uri = uri[uri.index('#')+1:]
    elif ':' in uri:
      uri = uri[uri.index(':')+1:]
    return self.shorten_terms(uri)

  def formatjson(self, j, depth=0):
    #logging.info("%sformatjson on %s", '  '*depth, repr(j))
    ret = None
    if isinstance(j, dict):
      assert('name' in j and 'args' in j)
      assert(len(j['args']) > 0)
      ret = "{}({})".format(j['name'], ','.join([ self.formatjson(x, depth+1) for x in j['args'] ]))
    elif isinstance(j, list):
      ret = "[{}]".format(' , '.join([ self.formatjson(x, depth+1) for x in j ]))
    elif isinstance(j, str):
      ret = self.shorten_uri(j)
    else:
      ret = repr(j)
    #logging.info("%sformatjson on %s returned %s", '  '*depth, repr(j), ret)
    return ret

  def print_table(self, t):
    # get all rows and all columns
    all_rows = list(sorted(t.keys(), key = lambda x: int(x)))
    all_columns = list(sorted(set([ c for v in t.values() for c in v.keys() ])))

    def format_single(s):
      if isinstance(s,str) and s[0] == '"':
        return self.shorten_uri(s)
      elif isinstance(s,dict) and s['name'] == '()':
        return '|'.join([ self.shorten_uri(x) for x in s['args'] ])
      else:
        return self.formatjson(s)

    def format_field(f):
      return '+'.join([ format_single(s) for s in f])

    grid = [ [ format_field(t[r][c]) for c in all_columns ] for r in all_rows ]
    df = pd.DataFrame(grid, columns=[ format_single(s) for s in all_columns ])
    pd.set_option('display.max_rows', None) # row count limit
    pd.set_option('display.max_columns', None) # column count limit
    pd.set_option('display.width', None) # terminal character width limit
    pd.set_option('display.max_colwidth', None) # terminal character width limit
    self.msg(str(df))

  def print_plan(self, answer):
    #logging.debug("answer %s", answer)
    bytime = collections.defaultdict(lambda: { 'actions': [], 'states': [], 'storages': {} })
    # { row: { column: [content1, content2, ...] } }
    table_data = collections.defaultdict(lambda: collections.defaultdict(list))
    for a in answer['atoms']:
      logging.debug("processing atom %s", a)
      handled = False
      if isinstance(a, dict):
        if a['name'] == 'table':
          assert(len(a['args']) == 3)
          row, col, info = [ self.formatjson(x) for x in a['args'] ]
          table_data[row][col].append(info)
          handled = True
        elif a['name'] in ['action']:
          assert(len(a['args']) == 2)
          spec, t = a['args']
          assert(isinstance(t, int))
          bytime[t]['actions'].append( spec )
          handled = True
        elif a['name'] in ['in']:
          #logging.warning("handling in: %s", a)
          assert(len(a['args']) == 3)
          what, where, t = a['args']
          assert(isinstance(t, int))
          bytime[t]['states'].append( (what, where) )
          handled = True

        elif a['name'] in ['storageContent']:

          if len(a['args']) != 3:
            logging.error("got atom %s with != 3 arguments! ignoring!", a)
            continue
          what, contentlist, t = a['args']

          if not isinstance(t, int):
            logging.error("got atom %s with argument 3 not an integer! ignoring!", a)
            continue

          logging.debug("storage %s", repr(contentlist))
          if contentlist == 'c':
            content = []
          elif isinstance(contentlist, dict) and contentlist['name'] == 'c':
            content = contentlist['args']
          else:
            logging.error('got uninterpretable storage %s', self.formatjson(contentlist))
          if what in bytime[t]['storages']:
            logging.error("got storage content %s and %s for storage %s/time %s! (inconsistency)", bytime[t]['storages'][what], content, what, t)
          else:
            bytime[t]['storages'][what] = content
          handled = True

        elif a['name'] in ['storageContentAt']:

          if len(a['args']) != 4:
            logging.error("got atom %s with != 4 arguments! ignoring!", a)
            continue
          what, position, content, t = a['args']

          if not isinstance(t,int) or not isinstance(position,int):
            logging.error("got atom %s with argument 2 or 3 not an integer! ignoring!", a)
            continue

          # create storage
          if what not in bytime[t]['storages']:
            bytime[t]['storages'][what] = []
          # extend to required length
          while len(bytime[t]['storages'][what]) <= position:
            bytime[t]['storages'][what].append(None)
          if bytime[t]['storages'][what][position] is not None:
            logging.error("got storage content %s at index %d and existing content %s for storage %s/time %s! (inconsistency)", bytime[t]['storages'][what][position], position, content, what, t)
          else:
            bytime[t]['storages'][what][position] = content
          handled = True

        elif a['name'] == 'dbg':
          logging.warning("DEBUG ATOM: %s", self.formatjson(a))
          handled = True
      if not handled:
        logging.warning("unhandled atom: %s", a)

    if len(bytime) == 0:
      logging.warning("no timepoints found in answer set %s", answer)
    else:
      times = range(0, max(bytime.keys())+1)
      for t in times:
        self.msg("Time Step {}:".format(t))
        for what, where in bytime[t]['states']:
          self.msg("  location {} contains {}".format(self.formatjson(where), self.formatjson(what)))
        for what, contents in bytime[t]['storages'].items():
          self.msg("  storage {} contains {}".format(self.formatjson(what), self.formatjson(contents)))
        for a in bytime[t]['actions']:
          self.msg("  action "+self.formatjson(a))
      self.msg('')

    self.print_table(table_data)

def main():
  formatter = PlanFormatter()
  for line in sys.stdin:
    l = line.strip()
    if l == '':
      continue
    answer = json.loads(l)
    sys.stdout.write("\nAnswer Set with cost {}\n".format(str([ '{}@{}'.format(c['cost'], c['priority']) for c in answer['cost'] ])))
    formatter.print_plan(answer)
    sys.stdout.flush()

if __name__ == '__main__':
  main()
