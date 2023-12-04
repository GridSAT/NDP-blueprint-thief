#	configs.py
#
#	Non-Deterministic Processor (NDP) - efficient parallel SAT-solver
#	Copyright (c) 2023 GridSAT Stiftung
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU Affero General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU Affero General Public License for more details.
#
#	You should have received a copy of the GNU Affero General Public License
#	along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#	GridSAT Stiftung - Georgstr. 11 - 30159 Hannover - Germany - ipfs: gridsat.eth/ - info@gridsat.io
#

import logging
import uuid
import inspect, sys

MIN_LITERAL = 1

# input file format
INPUT_SL = 1
INPUT_SLF = 2
INPUT_DIMACS = 3

# database
DB_HOST="NAME"
DB_PORT=5432
DB_NAME="NAME"
DB_USER="NAME"
DB_PASSWORD="PASS"
GLOBAL_SETS_TABLE_PREFIX = "globalsetstable_"
GLOBAL_SETS_TABLE = GLOBAL_SETS_TABLE_PREFIX

# constants
NODE_UNIQUE = 0
NODE_REDUNDANT = 1
NODE_EVALUATED = 2
UNIQUE_COUNT = 0
REDUNDANT_COUNT = 1
REDUNDANT_HITS = 2

# modes
MODE_FLO = "flo"
MODE_FLOP = "flop"
MODE_LOU = "lou"
MODE_LO = "lo"
MODE_NORMAL = "normal"


# logging
#logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d %(funcName)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logging.basicConfig(format='%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger('NSS')
logger.setLevel(logging.WARNING)

# Error codes
SUCCESS = 1
DB_UNIQUE_VIOLATION = -1
DB_UNKNOWN_ERROR = -2

NOT_SABRY_FORMAT = -1
INCOMPATIBLE_TREE = -2


# generate problem ID
PROBLEM_ID = str(uuid.uuid4()).replace('-', '_')


### util functions ###

# format size 
def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

# get current object size in memory
def get_object_size(obj, seen=None):
    """Recursively finds size of objects in bytes"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if hasattr(obj, '__dict__'):
        for cls in obj.__class__.__mro__:
            if '__dict__' in cls.__dict__:
                d = cls.__dict__['__dict__']
                if inspect.isgetsetdescriptor(d) or inspect.ismemberdescriptor(d):
                    size += get_object_size(obj.__dict__, seen)
                break
    if isinstance(obj, dict):
        size += sum((get_object_size(v, seen) for v in obj.values()))
        size += sum((get_object_size(k, seen) for k in obj.keys()))
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum((get_object_size(i, seen) for i in obj))
        
    if hasattr(obj, '__slots__'): # can have __slots__ with __dict__
        size += sum(get_object_size(getattr(obj, s), seen) for s in obj.__slots__ if hasattr(obj, s))
        
    return size
