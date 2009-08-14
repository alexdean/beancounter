#!/usr/bin/python
import os, time
from shutil import copy

### USER CONFIGURATION ###
cur_file = '/proc/user_beancounters'
prev_file = '/var/local/user_beancounters.prev'
# cur_file = '/Users/alex/Code/backup/user_beancounters'
# prev_file = '/Users/alex/Code/backup/user_beancounters.prev'
##########################

# Unlikely.  http://wiki.openvz.org/UBC_failcnt_reset
class CounterResetError( Exception ):
  """Raised if current beancounter file has smaller failcnt values than previous file."""

# read a user_beancounters file, and return a {'key':'failcnt'} dict.
def get_beancounter_failcnt( filename ):
  values = {}
  fp = open( filename )
  for line in fp:
    arr = line.split()
    size = len( arr )
    # most rows have 6 cols.  row which includes container id has 7
    # skip Version, header, and dummy rows
    if ( size == 6 or size == 7 ) and arr[ -6 ] != 'resource' and arr[ -6 ] != 'dummy':
      values[ arr[ -6 ] ] = arr[ -1 ]
  return values

# compare 2 dicts created by get_beancounter_failcnt.
# return dict with differences
def beancounter_diff( prev, cur ):
  values = {}
  keys = prev.keys()
  for key in keys:
    diff = int( cur[ key ] ) - int( prev[ key ] )
    if diff > 0:
      values[ key ] = diff
    # if counter resets, value will be < 0
    # no facility is provided for resetting counters individually. If 1 is reset, they all are.
    elif diff < 0:
      raise CounterResetError
  return values

def output( message ):
  print '%s : %s' % ( time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime() ), message)

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
    keys = diffs.keys()
    for key in keys:
      output( "%(key)s %(diff)s %(prev)s -> %(cur)s" % {
        'key' : key.rjust( 12 ),
        'diff' : ( '+' + str( diffs[ key ] ) ).rjust( 8 ),
        'prev': str( prev_values[ key ] ).rjust( 8 ),
        'cur' : cur_values[ key ]
      } )

# cp new file to old file location
copy( cur_file, prev_file )