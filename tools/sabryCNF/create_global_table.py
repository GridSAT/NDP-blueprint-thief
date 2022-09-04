import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
#sys.path.append('..')
import DbAdaptor

table_name = "GlobalSetsTable_lo"
db_adaptor = DbAdaptor.DbAdapter()
db_adaptor.gs_create_table(table_name)