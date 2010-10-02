#!/usr/bin/python
import os, time, subprocess
from shutil import copy

### USER CONFIGURATION ###
cur_file = '/proc/user_beancounters'
prev_file = '/var/local/user_beancounters.prev'
# cur_file = '/Users/alex/Code/beancounter/user_beancounters'
# prev_file = '/Users/alex/Code/beancounter/user_beancounters.prev'
##########################

# Unlikely.  http://wiki.openvz.org/UBC_failcnt_reset
class CounterResetError( Exception ):
  """Raised if current beancounter file has smaller failcnt values than previous file."""

# convert numeric container ids to hostnames
# if conversion is not possible (vzlist not available), return ctid
class VzList:
  def __init__( self, input='' ):
    if input == '':
      try:
        input = subprocess.Popen( [ "/usr/sbin/vzlist" ], stdout=subprocess.PIPE ).communicate()[ 0 ]
      except OSError:
        pass
    lines = [ line.split() for line in input.split( "\n" ) ]
    self.map = dict( [ ( line[0], line[4] ) for line in lines if len( line ) == 5 ] )

  def hostname_for_ctid( self, ctid ):
    ret_val = ctid
    if ctid in self.map
      ret_val = self.map[ ctid ]
    return ret_val

# read a user_beancounters file, and return a { 101:{'key':'failcnt'}, 102:{'key':'failcnt' } dict.
def get_beancounter_failcnt( filename ):
  container = "unknown"
  values = {}
  fp = open( filename )
  for line in fp:
    arr = line.split()
    size = len( arr )
    # most rows have 6 cols.  row which includes container id has 7
    # skip Version, header, and dummy rows

    if size == 7 and arr[ -6 ] != 'resource' :
      # '101:' -> '101'
      container = arr[ -7 ][ 0:-1 ]
      values[ container ] = {}

    if ( size == 6 or size == 7 ) and arr[ -6 ] != 'resource' and arr[ -6 ] != 'dummy':
      values[ container ][ arr[ -6 ] ] = arr[ -1 ]

  return values

# compare 2 dicts created by get_beancounter_failcnt.
# return dict with differences
def beancounter_diff( prev, cur ):
  values = {}
  ctids = prev.keys()
  for ctid in ctids:
    keys = prev[ ctid ].keys()
    for key in keys:
      diff = int( cur[ ctid ][ key ] ) - int( prev[ ctid ][ key ] )
      if diff > 0:
        if ctid not in values:
          values[ ctid ] = {}
        values[ ctid ][ key ] = diff
      # if counter resets, value will be < 0
      # no facility is provided for resetting counters individually. If 1 is reset, they all are.
      elif diff < 0:
        raise CounterResetError
          
  return values

def output( message ):
  print '%s : %s' % ( time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime() ), message)

vzlist = VzList()

prev_values = {}
try:
  prev_values = get_beancounter_failcnt( prev_file )
  
except IOError:
  # should only happen on initial run.
  output( "*** Previous-values file does not exist.  Creating. ***" )

if prev_values:
  cur_values = get_beancounter_failcnt( cur_file )
  try:
    diffs = beancounter_diff( prev_values, cur_values )
  except CounterResetError:
    output( "***  Counters were reset.  ***" )
  else:
    ctids = diffs.keys()
    for ctid in ctids:
      for key in diffs[ ctid ]:
        output( "%(ctid)s\t%(key)s\t%(diff)s\t%(prev)s -> %(cur)s" % {
          'ctid' : vzlist.hostname_for_ctid( ctid ),
          'key' : key,
          'diff' : ( '+' + str( diffs[ ctid ][ key ] ) ),
          'prev': str( prev_values[ ctid ][ key ] ),
          'cur' : cur_values[ ctid ][ key ]
        } )

# cp new file to old file location
copy( cur_file, prev_file )
