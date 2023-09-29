#	SuperQueue.py
#
#	Non-Deterministic Processor (NDP) - efficient parallel SAT-solver
#	Copyright (c) 2022 GridSAT Stiftung
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU Affero General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.

#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU Affero General Public License for more details.
#
#	You should have received a copy of the GNU Affero General Public License
#	along with this program.  If not, see <https://www.gnu.org/licenses/>.

#	GridSAT Stiftung - Georgstr. 11 - 30159 Hannover - Germany - ipfs: gridsat.eth/ - info@gridsat.io
#

import time
import Set
from DbAdaptor import DbAdapter
from configs import PROBLEM_ID
from collections import deque
from collections import OrderedDict
from ordered_set import OrderedSet

''' Queue that uses both memory and database to hold big number of object efficiently '''
# will save ids in memory, while the objects will be saved in DB

# tip: a nice command to get the size of a table in bytes: SELECT pg_size_pretty(pg_relation_size('foo'));

class SuperQueue:

    use_runtime_db = False

    def __init__(self, unique_queue=False, use_runtime_db=False, problem_id=PROBLEM_ID):

        self.unique_queue = unique_queue
        if unique_queue:            
            self.objqueue = OrderedSet()
            self.idsqueue = OrderedSet()   # queue of objects ids
        else:
            self.objqueue = deque()   # queue of objects
            self.idsqueue = deque()   # queue of objects ids
                            
        self.table_name = "queue_{}_{}".format(problem_id, str(time.time()).replace(".", ""))
        self.use_runtime_db = use_runtime_db
        if use_runtime_db:
            self.db = DbAdapter()
            self.db.rtq_create_table(self.table_name)
        

    def __del__(self):
        #drop table
        if self.use_runtime_db:
            self.db.rtq_cleanup(self.table_name)

    def insert(self, item):
        will_add_new_item = True
        # in case of unique queue, make sure to add to the database only when new item is added
        if self.unique_queue and len(self.idsqueue) > self.idsqueue.append(item):
            will_add_new_item = False

        if will_add_new_item:
            if self.use_runtime_db:
                self.idsqueue.append(item.id)
                self.db.rtq_insert_set(self.table_name, item.id, item.to_string(pretty=False), item.serialize_properties())
            else:
                self.objqueue.append(item)
            
        return True

    def pop(self):
        item = None        
        if self.use_runtime_db:
            objid = None
            if self.unique_queue:
                objid = self.idsqueue[0]
                self.idsqueue.remove(objid)
            else:
                objid = self.idsqueue.popleft()
            id, body, properties = self.db.rtq_get_set(self.table_name, objid)
            item = Set.Set(body, properties=properties)
            item.id = id

        elif self.unique_queue:
            item = self.objqueue[0]
            self.objqueue.remove(item)
        else:
            item = self.objqueue.popleft()

        return item

    def size(self):
        size = 0
        if self.use_runtime_db:
            size = len(self.idsqueue)
        else:
            size = len(self.objqueue)

        return size

    def is_empty(self):
        return not bool(self.size())
