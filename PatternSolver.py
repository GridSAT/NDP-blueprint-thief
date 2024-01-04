#	PatternSolver.py
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

import os, gc
import sys
import time, math
from datetime import datetime, timezone
import psutil
import binascii
from collections import defaultdict
from graphviz import Digraph
from queue import Queue
from configs import *
from DbAdaptor import DbAdapter
import SuperQueue
from Set import Set
import traceback
import psycopg2
import math
import ray


# TODO:
#
# - About the check if a node exist in the global DB, I need to implement it with another option to issue a query to gdb to check existice of the node,
#   instead of loading all the nodes from the gdb and occupy lots of memory.
# - Solve the issue when a node is found in gdb, then determine the accurate unique_count and redundant count for parent nodes.
#   The problem is not trivial here, as the parent node might be pointing to another node down the path that is also found in the gdb. The second found node
#   could be a child of the first found node, and thus the first found node's unique cound already includes the unique counts of the second found node.
#   we need to be careful how to solve this issue to get the non overlapping unique count. A naive approche is to load all the tree from the gdb and walk on it exactly as
#   we do in construct_graph_stats(). It's slow but easy and guaranteed solution. I think the solution of this problem relates to graph reachability problem in algorithms
#   where we need to determine the count of all reachable nodes for each node of the graph, I couldn't find any solution faster than O|V*E|. That's how I implemented
#   construct_graph_stats() here. But I'm hoping to find an optimized solution specific for our scenario that gives a faster solution.
#   So far, this issue of integrating the unique count of a saved gdb node is not properly implemented.
#
# * RunTimeQueue_{random int}: Which will contain the queue of nodes to be processed. This is an ephermal table that will be dropped at the end of execution. Each row has:
#       - set_id   // PRIMARY, a number represent the order of the set to maintain breadth first evaluation
#       - set_body (string repr. of the set)
#
# - Upon execution, load list of hashes from GlobalSetsTable for sets of no. of clauses <= no. of clauses of root input set. This would be "nodes seen" dict,
#   any new node will be add to the dict.
# - new nodes will also be added to another structure in memory called to be purged later into the database when it reach a reasonable big size
#   to batch insert operations in GlobalSetsTable
# - DbAdaptor constructor should set the self.global_table_name rather than sending it in every method's param
#  - enable multiple Ray Clusters
#  - enable GPU

TRUE_SET_HASH = Set.calculate_hash('T')
FALSE_SET_HASH = Set.calculate_hash('F')


# Declare a global variable for CPU count
CPU_COUNT = None

# Get the number of CPUs from the Ray cluster
cluster_resources = ray.cluster_resources()
CPU_COUNT = cluster_resources.get("CPU", 1)  # Defaults to 1 if not available

# An object represent a node in the graph
class Node:

	def __init__(self):
		self.seen_count = 1
		self.parents = []
		self.seen_count = 1
		self.status = NODE_UNIQUE
		self.subgraph_uniques = 1
		self.subgraph_redundants = 0

		# one of its decendants is a redundant, but it could be redundant with another subgraph
		# has_potential_redundant is a flag that bubbles up from decendants to the parent.
		# if a parent node found two children with the flag set to True, it means it has a redundant node in its subgraph
		self.has_potential_redundant = False

@ray.remote
class RemotePatternSolver():
	def __init__(self, pattern_solver, name='', node=None):
		self.pattern_solver = pattern_solver
		self.name = name
		self.node = node

	def do_get_node_subgraph_stats(self, root_id, node_ids, nodes_children):
		return self.pattern_solver.do_get_node_subgraph_stats(root_id, node_ids, nodes_children)

	def process_nodes_queue(self, input_mode=None, dot=None, sort_by_size=False, thief_method=False, break_on_squeue_size=0):
		return (self,) + self.pattern_solver.process_nodes_queue(self.node, input_mode, dot, generate_threads=False, name=self.name, is_sub_process=True, sort_by_size=sort_by_size, thief_method=thief_method, break_on_squeue_size=break_on_squeue_size)


class PatternSolverArgs:
	def __init__(self, args=None):
		self.exit_upon_solving = args.exit_upon_solving if args else False
		self.mode = args.mode if args else None
		self.start_mode = args.start_mode if args else None
		self.no_stats = args.no_stats if args else True
		self.quiet = args.quiet if args else True
		self.threads = args.threads if args else 0
		self.use_global_db = args.use_global_db if args else False
		self.use_runtime_db = args.use_runtime_db if args else False
		self.output_graph_file = args.output_graph_file if args else None
		self.output_solution_file = args.output_solution_file if args else None
		self.verbos = args.verbos if args else False
		self.verify = args.verify if args else False
		self.very_verbos = args.very_verbos if args else False
		self.sort_by_size = args.sort_by_size if args else False
		self.thief_method = args.thief_method if args else None


class PatternSolver:

	# the dictionary that holds processed set
	# currently each key is the string represenation of the set, i.e. set.to_string()
	seen_sets = {}          # stores all nodes in global db
	solved_sets = {}                        # stores solved sets pulled from global db
	graph = {}                              # stores the nodes as we solve them
	args = None
	db_adaptor = None
	problem_id = None
	use_runtime_db = False
	solution = None
	global_table_name = GLOBAL_SETS_TABLE

	def __init__(self, args=None, problem_id=PROBLEM_ID, cluster_resources=None, input_file=None):
		self.args = args

		self.input_file = input_file

		if problem_id:
			self.problem_id = problem_id

		if args.use_runtime_db:
			self.use_runtime_db = True

		if args.use_runtime_db or args.use_global_db:
			self.db_adaptor = DbAdapter()

		if args.mode:
			self.global_table_name = GLOBAL_SETS_TABLE_PREFIX + args.mode.lower()

		self.seen_sets.clear()
		self.reset()

		self.max_threads = self.get_cpu_count(args.threads)

		self.cluster_resources = cluster_resources if cluster_resources else ray.cluster_resources()

	def get_cpu_count(self, thread_arg):
		if thread_arg == 0:
			if ray.is_initialized():
				# Get the number of available CPU cores from Ray
				cluster_resources = ray.cluster_resources()
				return int(cluster_resources.get("CPU", 1))  # Convert to int, defaults to 1 if not available
			else:
				# Ray is not initialized, use system's CPU count
				return int(os.cpu_count() or 1)  # Defaults to 1 if os.cpu_count() returns None
		elif thread_arg > 1:
			return int(thread_arg)
		else:
			return 1

	def reset(self):
		self.is_satisfiable = False
		self.leaves = []
		# populate nodes_stats with defaults
		self.nodes_stats = defaultdict(lambda: [0,0,0])

		# vars to calculate graph size at the end
		self.uniques = self.redundant_hits = self.redundants = self.nodes_found_in_gdb = 0
		self.redundant_ids = {}  # ids of redundant nodes
		self.nodes_children = {} # children ids for every node

		self.started_processes = 0
		self.threads_count = 0
		self.start_creating_threads = False
		self.threads = []

	def draw_graph(self, dot, outputfile):
		fg = open(outputfile, "w")
		fg.write(dot.source)
		fg.close()

	def load_set_records(self, num_clauses):
			# load solved hashes
			solve_hashes = self.db_adaptor.gs_load_solved_sets(self.global_table_name, num_clauses)
			self.solved_sets = {el[0]:[el[1], el[2]] for el in solve_hashes}
			# load unsolved hashes
			unsolve_hashes = self.db_adaptor.gs_load_unsolved_sets(self.global_table_name, num_clauses)
			self.seen_sets = {el:1 for el in unsolve_hashes}
			# combine solved and unsolved in seen_sets map
			self.seen_sets.update({el:1 for el in self.solved_sets.keys()})

	def get_children_from_gdb(self, set_hash, db_adaptor=None):
		if db_adaptor == None:
			db_adaptor = self.db_adaptor

		result = ()
		children = db_adaptor.gs_get_children(self.global_table_name, set_hash)
		for child_hash in children:
			if child_hash == None:
				return (None, None)

			child = Set()
			if child_hash == TRUE_SET_HASH:
				child.value = True
			elif child_hash == FALSE_SET_HASH:
				child.value = False
			else:
				# get the body from the db
				set_data = db_adaptor.gs_get_set_data(self.global_table_name, child_hash)
				if set_data == None:
					return (None, None)

				child = Set(set_data['body'])
				child.computed_hash = child_hash

			result = result + (child, )

		return result

	def is_in_graph(self, set_hash):
		return (self.nodes_children.get(set_hash, False) != False)

	def is_set_in_gdb(self, set_hash, db_adaptor=None):
		if db_adaptor == None:
			db_adaptor = self.db_adaptor
		if self.args.gdb_no_mem:
			return db_adaptor.gs_does_hash_exist(self.global_table_name, set_hash)
		return self.seen_sets.get(set_hash, False)

	def is_set_solved(self, set_hash, db_adaptor=None):
		if db_adaptor == None:
			db_adaptor = self.db_adaptor
		if self.args.gdb_no_mem:
			return db_adaptor.gs_is_hash_solved(self.global_table_name, set_hash)
		return self.solved_sets.get(set_hash, False)

	def save_parent_children(self, cnf_set, child1_hash, child2_hash, db_adaptor=None):


		# Don't waste time
		if not self.args.use_global_db:
			return SUCCESS

		if db_adaptor == None:
			db_adaptor = self.db_adaptor

		cnf_hash = cnf_set.get_hash()
		num_of_vars = 0
		if len(cnf_set.clauses):
			num_of_vars = abs(cnf_set.clauses[-1].raw[-1])

		# save the set in global DB if it's not there already
		if self.args.use_global_db and not self.is_set_in_gdb(cnf_hash, db_adaptor):
			return db_adaptor.gs_insert_row(self.global_table_name,
										 cnf_hash,              # set hash
										 cnf_set.to_string(pretty=False),   # set body
										 child1_hash,           # child 1 hash
										 child2_hash,           # child 2 hash
										 [],                    # mapping, to be added
										 len(cnf_set.clauses),  # count of clauses
										 num_of_vars)

		return SUCCESS

	def get_node_subgraph_stats_iterative(self, node_id, nodes_children, node_descendants, node_redundants):

		stack = [node_id]
		while stack:
			current_node_id = stack.pop()
			if current_node_id in node_descendants:
				node_redundants[current_node_id] += 1
				continue
			else:
				node_descendants[current_node_id] = 1
				stack.extend(nodes_children.get(current_node_id, []))

	def do_get_node_subgraph_stats(self, root_id, node_ids, nodes_children):

		result = []

		for node_id in node_ids:
			node_descendants = {}
			node_redundants = defaultdict(int)
			self.get_node_subgraph_stats_iterative(node_id, nodes_children, node_descendants, node_redundants)
			result.append( (node_id, len(node_descendants), len(node_redundants), sum(node_redundants.values()), (node_redundants if node_id == root_id else None)) )

		return result

	def construct_graph_stats(self, root_id, nodes_children, max_threads):

		root_node_redundants = {}

		# Retrieve the number of CPUs from the Ray cluster
		cpu_count = self.get_cpu_count(self.args.threads)
		max_stats = cpu_count
		#max_stats = 1 if max_threads < 2 else max_threads if max_threads < 12 else 12
		split_count = 100000

		keys = []
		subkeys = []

		for node_id in self.nodes_children.keys():
			subkeys.append(node_id)
			if len(subkeys) >= split_count:
				keys.append(subkeys)
				subkeys = []

		if len(subkeys):
			keys.append(subkeys)

		if self.args.verbos:
			print("Generating stats within ", len(keys), " processes each per ", split_count, "IDs ...")

		threads = []
		finished_stats = 0

		while len(keys) and (len(threads) < max_threads):
			rps = RemotePatternSolver.remote(PatternSolver(args=PatternSolverArgs()))
			threads.append(rps.do_get_node_subgraph_stats.remote(root_id, keys.pop(0), nodes_children))

		while len(threads):
			done_id, threads = ray.wait(threads)
			results = ray.get(done_id[0])

			for result in results:
				node_id, len_node_descendants, len_node_redundants, sum_node_redundants_values, res_root_node_redundants = result

				if not self.nodes_stats[node_id]:
					self.nodes_stats[node_id][UNIQUE_COUNT]     = 0
					self.nodes_stats[node_id][REDUNDANT_COUNT]  = 0
					self.nodes_stats[node_id][REDUNDANT_HITS]   = 0

				self.nodes_stats[node_id][UNIQUE_COUNT]     += len_node_descendants
				self.nodes_stats[node_id][REDUNDANT_COUNT]  += len_node_redundants
				self.nodes_stats[node_id][REDUNDANT_HITS]   += sum_node_redundants_values

				if res_root_node_redundants is not None:
					root_node_redundants = res_root_node_redundants

			while len(keys) and (len(threads) < max_threads):
				rps = RemotePatternSolver.remote(PatternSolver(args=PatternSolverArgs()))
				threads.append(rps.do_get_node_subgraph_stats.remote(root_id, keys.pop(0), nodes_children))

			finished_stats += 1

			if self.args.verbos:
				print("Completed stats processes:", finished_stats)

		if self.args.verbos:
			print()

		return root_node_redundants

	def save_in_global_db(self, root_redundants):

		for node_id in self.nodes_stats.keys():
			unique_nodes    = self.nodes_stats[node_id][UNIQUE_COUNT]
			redundant_nodes = self.nodes_stats[node_id][REDUNDANT_COUNT]
			redundant_hits  = self.nodes_stats[node_id][REDUNDANT_HITS]
			self.db_adaptor.gs_update_count(self.global_table_name, unique_nodes, redundant_nodes, redundant_hits, node_id)

		# saving redundants hits for redundant nodes
		for red_id, redundant_times  in root_redundants.items():
			self.db_adaptor.gs_update_redundant_times(self.global_table_name, redundant_times, red_id)


	def process_nodes_queue(self, cnf_set, input_mode, dot, generate_threads=False, name="main", is_sub_process=False, sort_by_size=False, thief_method=False, break_on_squeue_size=0):

		nodes_children = {}
		is_satisfiable = False
		solution = None
		starting_len = len(cnf_set.clauses)

		db_adaptor = self.db_adaptor
		try:
			squeue = SuperQueue.SuperQueue(name=name, use_runtime_db=self.use_runtime_db, problem_id=cnf_set.get_hash().hex())
			squeue.insert(cnf_set)
			nodes_children[cnf_set.id] = []

		except (Exception, psycopg2.DatabaseError) as error:
			logger.error("DB Error: " + str(error))
			logger.critical("Error - {0}".format(traceback.format_exc()))
			db_adaptor = None
			if is_sub_process:
				return None, None, None
			return False

		while not squeue.is_empty() and (not (is_sub_process and break_on_squeue_size > 0 and squeue.size() >= break_on_squeue_size)) and (not (bool(solution) & self.args.exit_upon_solving)):

			cnf_set = squeue.pop()
			logger.debug("Set #{0}".format(cnf_set.id))

			## Evaluate
			## check first if the set is unsolved in the global db. If so, just grab the children from there.
			## if it's solved in gdb, it wouldn't be here in this loop at the first place.
			s1 = s2 = None
			## although this step is working fine, but it slower down the program, so there's no need.
			children_pulled_from_gdb = False
			if self.args.use_global_db and self.is_set_in_gdb(cnf_set.get_hash(), db_adaptor):
				(s1, s2) = self.get_children_from_gdb(cnf_set.get_hash(), db_adaptor)
				if s1 != None or s2 != None:
					logger.info("children pulled from gdb")
					self.nodes_found_in_gdb += 1
					children_pulled_from_gdb = True

			# TIME CONSUMER 1 sec
			if not children_pulled_from_gdb:
				(s1, s2) = cnf_set.evaluate()

			for child in (s1, s2):
				# TIME CONSUMER 0.1 sec
				child_str_before = child.to_string()

				# check if the set is already evaluated to boolean value
				if child.value != None:
					child.status = NODE_EVALUATED

					# solution is FOUND! .. save solution if satisfiable
					if child.value == True and solution == None:
						solution = child.evaluated_vars
						# sort by key
						solution = dict(sorted(solution.items()))
						if self.args.verbos:
							logger.info(f"\nProcess '{name}' found the solution!\n")

				else:
					if not children_pulled_from_gdb:
						# TIME CONSUMER 1+ sec
						child.to_lo_condition((self.args.start_mode if generate_threads or (break_on_squeue_size > 0) else input_mode), sort_by_size, thief_method)
						# TIME CONSUMER 0.1 sec
						child_hash = child.get_hash(force_recalculate=True)

					# if chid pulled from gdb, no need to recompute the hash to save time
					child_hash = child.get_hash()
					child.id = child_hash
					# check if we have processed the set before
					if nodes_children.get(child_hash, False) != False:
						child.status = NODE_REDUNDANT
					else:
						child.status = NODE_UNIQUE

				child_str_after = child.to_string()
				child_hash = child.get_hash()

				if child.status == NODE_UNIQUE:
					self.uniques += 1
					nodes_children[child.id] = []
					nodes_children[cnf_set.id].append(child.id)

					if self.args.output_graph_file:
						#dot.node(child.id.hex(), child_str_before + "\\n" + child_str_after, color='black')
						dot.node(child.id.hex(), child_str_before + "\\n" + child_str_after + "\\n" + f"fnm = {child.final_names_map}" + "\\n" + \
						f"ov = {child.original_values}" + "\\n" + f"sol = {child.evaluated_vars}, highest occuring var = {child.highest_occurring_var}", color='black')
						dot.edge(cnf_set.id.hex(), child.id.hex())

				elif child.status == NODE_REDUNDANT:
					self.redundant_hits += 1
					self.redundant_ids[child.id] = 1
					nodes_children[cnf_set.id].append(child.id)

					if self.args.output_graph_file:
						dot.node(child.id.hex(), color='red')
						dot.edge(cnf_set.id.hex(), child.id.hex())

				elif child.status == NODE_EVALUATED:
					if child.value == True:
						is_satisfiable = True
					if self.args.output_graph_file:
						child.id = child.to_string()
						dot.node(str(child.id), child.to_string())
						dot.edge(cnf_set.id.hex(), child.id)

			# CNF nodes in this loop are all unique, if they weren't they wouldn't be in the queue
			# if insertion in the global table is successful, save children in the queue,
			# otherwise, the cnf_set is already solved in the global DB table
			global_save_status = self.save_parent_children(cnf_set, s1.get_hash(), s2.get_hash(), db_adaptor)
			if global_save_status == SUCCESS:
				for child in (s1, s2):
					if child.status == NODE_UNIQUE:
						squeue.insert(child)
						#if max_threads > 0 and master_threads and len(master_threads) < max_threads:
						#    print()

			elif global_save_status == DB_UNIQUE_VIOLATION:
				logger.debug("Node #{} is already found 'during execution' in global DB.".format(cnf_set.id))

			# if both children are boolean, then cnf_set is a leaf node
			if s1.value != None and s2.value != None:
				self.leaves.append(cnf_set.id)

			if False and self.args.verbos:
				logger.info(f"Process '{name}': Progress {round((1-len(cnf_set.clauses)/starting_len)*100)}%, nodes so far: {self.uniques:,} uniques and {self.redundant_hits:,} redundant hits...",)

			if self.args.verbos and (len(nodes_children) % 20 == 0): # and not is_sub_process:
				logger.info(f"Process '{name}': Progress {round((1-len(cnf_set.clauses)/starting_len)*100)}% | nodes: {len(nodes_children)} | squeue: {squeue.size()} | uniques: {self.uniques:,} | redunt: {self.redundant_hits:,}...",)

			# if number of running threads less than limit and less than queue size, create a new thread here and call process_nodes_queue
			if generate_threads and (squeue.size() >= (self.max_threads if self.max_threads < 32 else 32)):

				if squeue.size() > 1.5 * self.max_threads:
					generate_threads = False

				print()
				threads_to_create = int(squeue.size()) if squeue.size() < self.max_threads else int(self.max_threads)

				for n in range(0, threads_to_create):
					i = self.started_processes
					self.started_processes=self.started_processes + 1

					logger.info(f"Creating process {i}")
					cnf_set = squeue.pop()
					rps = RemotePatternSolver.remote(PatternSolver(args=PatternSolverArgs(self.args)), name=f'Process #{i}', node=cnf_set)
					self.threads.append(rps.process_nodes_queue.remote(input_mode=input_mode, dot=dot, sort_by_size=sort_by_size, thief_method=thief_method, break_on_squeue_size=(8 if generate_threads else 0)))

				while len(self.threads):

					done_id, self.threads = ray.wait(self.threads)
					rps, process_squeue, process_is_satisfiable, process_nodes_children, process_solution = ray.get(done_id[0])

					logger.info(f"{rps.name} retrieving queue...")
					logger.info(f"{rps.name} done.")

					# Return to db after serialization
					process_squeue.relink_db()

					# in case the child process exited before it solve the problem, and get the main process to solve it
					if process_nodes_children == None and not process_solution:
						squeue.insert(rps.node)
					else:
						for k in process_nodes_children.keys():
							if nodes_children.get(k, False) and len(nodes_children[k]) >= len(process_nodes_children[k]):
								continue
							nodes_children[k] = process_nodes_children[k]

						if process_is_satisfiable != None:
							is_satisfiable |= process_is_satisfiable

						#solution = process_solution
						if process_solution:
							solution = process_solution
							if self.args.exit_upon_solving:
								logger.info("Terminating all processes....")
								break

					# check for not ready sub queue
					while (process_squeue.size() > 0):
						squeue.insert(process_squeue.pop())

					if self.args.verbos and not is_sub_process:
						logger.info(f"Process '{name}': Progress {round((1-len(cnf_set.clauses)/starting_len)*100)}% | nodes: {len(nodes_children)} | squeue: {squeue.size()} | uniques: {self.uniques:,} | redunt: {self.redundant_hits:,}...",)

					# when no more thread should be generate, check and run if more work is available
					if not generate_threads:
						while (len(self.threads) < self.max_threads) and (squeue.size() > 0):
							i = self.started_processes
							self.started_processes=self.started_processes + 1

							logger.info(f"Creating process {i}")
							cnf_set = squeue.pop()
							rps = RemotePatternSolver.remote(PatternSolver(args=PatternSolverArgs(self.args)), name=f'Process #{i}', node=cnf_set)
							self.threads.append(rps.process_nodes_queue.remote(input_mode=input_mode, dot=dot, sort_by_size=sort_by_size, thief_method=thief_method))

						if len(self.threads) > 0:
							logger.info(f"\nNew tasks distributed, currently running processes: {len(self.threads)}\n")

		if is_sub_process:
			logger.info(f"Process {name} data is sent to the main process")
			logger.info(f"Process {name} is completed!")
			# remove the DBAdapter() while not serializable
			squeue.unlink_db()
			# return serializable values
			return squeue, is_satisfiable, nodes_children, solution
		else:
			self.is_satisfiable = is_satisfiable
			self.nodes_children = nodes_children
			self.solution       = solution
			logger.info(f"\n\nNon-Deterministic Processing completed!\n")

	@staticmethod
	def format_duration(seconds):
		minutes, seconds = divmod(seconds, 60)
		hours, minutes = divmod(minutes, 60)
		days, hours = divmod(hours, 24)
		if days > 0:
			return "{:.0f} days, {:.0f} hours".format(days, hours)
		if hours > 0:
			return "{:.0f} hours, {:.0f} minutes".format(hours, minutes)
		if minutes > 0:
			return "{:.0f} minutes, {:.0f} seconds".format(minutes, seconds)
		return "{:.2f} seconds".format(seconds)

	def solve_set(self, root_set):

		num_vars = len(root_set.get_variables())
		num_clauses = len(root_set.clauses)

		# Get current UTC time and convert it to a timestamp
		utc_now = datetime.now(timezone.utc)
		utc_zulu_time = utc_now.strftime("%Y-%m-%d %H:%M:%S %Z")

		# Start timing the entire process
		start_time = time.time()
		eval_time = None

		logger.info(f"\n\nSolving problem ID: {self.problem_id}\n")

		# graph drawing
		graph_attr={}
		graph_attr["splines"] = "polyline"
		dot = Digraph(comment='The CNF-tree', format='svg', graph_attr=graph_attr)

		logger.debug("Set #1 - to root set to {} mode".format(self.args.mode))
		setbefore = root_set.to_string()

		# create a map of variables, root node has a default map of a variable to itself
		vars = root_set.get_variables()
		root_set.original_values = dict(zip(vars, vars))

		root_set.to_lo_condition(self.args.mode, self.args.sort_by_size, self.args.thief_method)
		setafterhash = root_set.get_hash(force_recalculate=True)
		root_set.id = setafterhash

		input_mode = self.args.mode
		# if user input mode is MODE_LO, it means only root is LO and the rest are LOU, and since this is a child node, then pass LOU argument
		if self.args.mode == MODE_LO:
			input_mode = MODE_LOU

		self.uniques += 1

		# db_adaptor = DbAdapter() if self.use_db_adaptor else None

		# use global sets table
		if self.args.use_global_db:
			# create the table if not exist
			db_adaptor.gs_create_table(self.global_table_name)
			if not self.args.gdb_no_mem:
				self.load_set_records(len(root_set.clauses))

		# check if we have processed the CNF before
		if not self.is_set_solved(setafterhash):
			if self.args.output_graph_file:
				setafter = root_set.to_string()
				dot.node(setafterhash.hex(), setbefore + "\\n" + setafter, color='black')

			## Processing the nodes ##
			# Note about multithreading:
			# Multithreading in python doesn't take advantage of multi core hardware very well. Read: http://python-notes.curiousefficiency.org/en/latest/python3/multicore_python.html
			# So the solution I implemented here is to use multiprocessing instead of multithreading. In multiprocessing, python uses a core for each process
			# but processes don't have shared memory. So in order to make a repository for the pieces of solution, I used the global DB
			# each small process saves its subgraph solution in the DB. After that, I restart the code again without using multiprocess.
			# This way, only very few nodes will be evaluated at the beginning and then the rest is pulled from the DB without evaluation.
			# EDIT: I used a queue to pass the result of each process at the end of its execution. This worked very well!

			if self.max_threads:
				logger.info(f"\n\nNumber of processes = {self.max_threads}\n\n")

			# Main computation to process the root node
			self.process_nodes_queue(root_set, input_mode, dot, bool(self.max_threads), sort_by_size=self.args.sort_by_size, thief_method=self.args.thief_method)

			# Stats timing
			eval_time = time.time()

			if self.max_threads:
				#logger.info("\nNon-Deterministic Processing completed!\n")
				logger.info("CPUs utilized: {}\n".format(self.max_threads))

			### Solving the set is done, let's get the number of unique and redundant nodes
			if self.args.verbos:
				logger.info("\n=== Generating node stats...")

			if not self.args.no_stats:
				if self.args.verbos:
					logger.info("=== Generating subgraph stats...\n")

				logger.info(f"Current recursion limit = {sys.getrecursionlimit()}")
				logger.info(f"Setting recursion limit to {sys.getrecursionlimit() * 2}")

				sys.setrecursionlimit(sys.getrecursionlimit() * 2)
				root_redundants = self.construct_graph_stats(root_set.id, self.nodes_children, self.max_threads)

				self.uniques = self.nodes_stats[root_set.id][UNIQUE_COUNT]
				self.redundants = self.nodes_stats[root_set.id][REDUNDANT_COUNT]
				self.redundant_hits = self.nodes_stats[root_set.id][REDUNDANT_HITS]

				if self.args.verbos:
					logger.info("=== Done getting stats. ===")

				if self.args.use_global_db:
					if self.args.verbos:
						logger.info("=== Saving the final result in the global DB...")

					self.save_in_global_db(root_redundants)

		else:

			if self.args.verbos:
				logger.info("Input set is found in the global DB")
				logger.info("Pulling Set's data from the DB...")
			self.nodes_found_in_gdb = 1
			if db_adaptor is None:
				self.uniques = -1
				self.redundants = -1
				self.redundant_hits = -1
			set_data = self.db_adaptor.gs_get_set_data(self.global_table_name, setafterhash)
			self.uniques = set_data["unique_nodes"]
			self.redundants = set_data["redundant_nodes"]
			self.redundant_hits = set_data["redundant_hits"]

		# Retrieve the number of CPUs from the Ray cluster
		cluster_resources = ray.cluster_resources()
		num_cpus = cluster_resources.get("CPU", 1)  # Defaults to 1 if not available

		# Determine satisfiability status	
		str_satisfiable = "NOT satisfiable."
		if self.is_satisfiable: str_satisfiable = "SATISFIABLE!"

		process = psutil.Process(os.getpid())
		memusage = process.memory_info().rss  # in bytes
		stats = '\\n' + "    CPU total: {}".format(int(num_cpus))
		stats += '\\n' + "CPUs utilized: {}\n".format(int(self.max_threads))
		stats += '\\n' + "  Memory used: {0} \n".format(sizeof_fmt(memusage))
		stats += '\\n' + ' Non-deterministic computation: {}'.format(PatternSolver.format_duration(eval_time - start_time))
		stats += '\\n' + '             Total script time: {}\n'.format(PatternSolver.format_duration(time.time() - start_time))
		stats += '\\n' + "   Problem ID: {0}".format(self.problem_id)
		stats += '\\n' + f"    Zulu Time: {utc_zulu_time}\n" #  Zulu time (UTC)
		stats += '\\n' + "   Input file: {} | VARs: {} | Clauses: {}".format(
			self.input_file or "None",
			num_vars,
			num_clauses
		)
		# Concatenating Solution Mode, Thief Method, Sort-by-Size Option, and Exit with 1st Assignment
		thief_status = " | thief" if self.args.thief_method else ""
		exit_upon_solving_status = " | 1st assignment (-e)" if self.args.exit_upon_solving else ""
		sort_by_size_status = " | ascending clause size order (-z)" if self.args.sort_by_size else ""
		stats += '\\n' + "Solution mode: {0}{1}{2}{3}\n".format(self.args.mode.upper(), thief_status, sort_by_size_status, exit_upon_solving_status)

		# Display solution if satisfiable
		stats += '\\n' + "The input set is {0}\n".format(str_satisfiable)
		if self.is_satisfiable:
			stats += '\\n' + "SOLUTION: {0}\n".format(self.solution)

		# Handle FACT option
		if self.args.factorize:
			if len(root_set.all_prime_factors) == 1 and root_set.all_prime_factors[0] == root_set.factorized_number:
				# Display Prime
				stats += '\\n' + f"Input number {root_set.factorized_number} is prime! (no factors)\n\n"
			elif hasattr(root_set, 'rsa_factors') and root_set.rsa_factors:
			# Display RSA factors
				stats += f"\nRSA factors of {root_set.factorized_number}: {root_set.rsa_factors[0]} x {root_set.rsa_factors[1]}\n"
			elif len(root_set.all_prime_factors) > 1:
				# Display all factors
				factorization_str = " x ".join(map(str, root_set.all_prime_factors))
				stats += '\\n' + f"FACT: {root_set.factorized_number} = {factorization_str}\n\n"

		# Check if the multiply option is used and if a solution is found
		if self.args.multiply and self.solution:
			result_bits_values = [int(self.solution[v]) for v in root_set.multiply_result_bits]
			result = int(''.join(str(i) for i in result_bits_values)[::-1], 2)

			# Retrieve the multiplication factors provided as input arguments
			fact1 = self.args.multiply[0]
			fact2 = self.args.multiply[1]

			# Check if the calculated result matches the multiplication of fact1 and fact2
			if result == fact1 * fact2:
				# If the multiplication is correct, display the result
				stats += '\\n' + f"MULT: {fact1} x {fact2} = {result}\n\n"
			else:
				# If there is a discrepancy in the result, indicate a potential bug
				stats += '\\n' + f"Something is wrong. Probably a bug! Inputs {fact1} and {fact2} don't multiply to {result}!"

		# If the multiply option is used but no solution is found
		elif self.args.multiply:
			# Display a message indicating the input numbers cannot be multiplied based on the CNF input
			stats += '\\n' + f"The input numbers {self.args.multiply[0]} and {self.args.multiply[1]} can't be multiplied on the input CNF."

		stats += '\\n' + f"===== UNIQUE NODES: {len(self.nodes_children):,} =====\n"
		# Only include detailed stats and gdb info if gdb is used
		if not self.args.no_stats:
			stats += "\\n" + "redundant subtrees: {0}".format(self.redundants)
			stats += "\\n" + "    redundant hits: {0}\\n".format(self.redundant_hits)
			if self.args.use_global_db:
				stats += "\\n" + "Number of nodes found in gdb: {0}".format(self.nodes_found_in_gdb)
			stats += "\n"  # Add a new line at the end for formatting

		# draw graph
		if self.args.output_graph_file:
			dot.node("stats", stats, shape="box", style="dotted")
			self.draw_graph(dot, self.args.output_graph_file)

		if self.args.quiet_but_unique_nodes:
			logger.info(self.uniques)

		if self.args.quiet == False:
			logger.info("\nNDP output:")
			logger.info(stats.replace("\\n", "\n"))

	# format the solution for storage
	def format_solution(self, solution):
		true_vars = []
		false_vars = []
		result = ""
		for k,v in self.solution.items():
			if v == True:
				true_vars.append(str(k))
			else:
				false_vars.append(str(k))

		if true_vars:
			result = "T:"+ ','.join(true_vars) + "\n"
		if false_vars:
			result += "F:"+ ','.join(false_vars)

		return result

	def verify_solution(self, CnfSet, solution):
		true_vars = []
		false_vars = []
		for k,v in self.solution.items():
			if v == True:
				true_vars.append(k)
			else:
				false_vars.append(k)

		for s in CnfSet.clauses:
			result = False
			for v in s.raw:
				if (v > 0 and v in true_vars) or (v < 0 and abs(v) in false_vars):
					result = True

			if not result:
				return False

		return True
