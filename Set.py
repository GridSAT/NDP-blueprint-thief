#	Set.py
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

import hashlib
import ast
from configs import *
from Clause import *
import functools 

class Set:
    

    def __init__(self, str_input=None, id=0, properties=None):

        self.clauses = []
        self.value = None
        self.id = id
        self.computed_hash = None
        self.final_names_map = []
        self.evaluated_vars = {}
        self.original_values = {}
        self.highest_occurring_var = 1

        # create a Set object from input string
        if str_input:
            seq = str_input
            try:
                seq = seq.replace('(', '')
                seq = seq.replace(')', '')
                clauses = seq.split('&')
                clauses_set = []
                for cl in clauses:
                    s = cl.split('|')
                    # remove duplicates within clause
                    s = frozenset(map(int, s))
                    
                    # adding in a set container will remove duplicate clauses but will shuffle input order, so don't do it   
                    clauses_set.append(s)

                # create clauses objects
                i = 1
                for cl in clauses_set:
                    c = Clause(cl)
                    c.initial_index = i
                    self.add_clause(c)
                    i += 1

            except Exception as e:
                print("Error: " + str(e))


        if properties:
            self.deserialize_properties(properties)


    # deserialize set's properties when retrieved from the DB
    # As of now we have 3 properties: evaluated_vars, original_vars, final_names_map
    # are stored as string in order, all are concatenated using '|'
    def deserialize_properties(self, properties):
        self.evaluated_vars = {}
        self.original_values = {}
        self.final_names_map = []
        
        evaluated_vars, original_values, final_names_map = properties.split('|')

        ### get evaluated_vars
        if evaluated_vars:
            # input evaluated vars should be in the format [comma delimited true variables]-[comma delimited false variables]
            # for example: '1,3,5,2-6,4' => {1:true, 3:true, 5:true, 2:true, 6:false, 4:false}
            true_vars, false_vars = evaluated_vars.split('-')
            flag = True
            for vars in (true_vars, false_vars):
                if vars:
                    self.evaluated_vars.update({v:flag for v in list(map(int, vars.split(',')))})
                flag = not flag

        ### get original_values
        if original_values:
            #example format: {2:5,3:6,4:1,5:8,6:2,7:7,8:4,9:9}
            self.original_values = ast.literal_eval(original_values)

        ### get final_names_map
        if final_names_map:
            # example format: [2,3,4,5,6,7,8,9]
            self.final_names_map = ast.literal_eval(final_names_map)


    # convert evaluated_vars, original_values and final_names_map to string for DB storage
    def serialize_properties(self):
        
        ### evaluated_vars
        # convert evaluated vars of this set into string for DB storage
        # the format is [comma delimited true variables]-[comma delimited false variables]
        true_ev_vars = []
        false_ev_vars = []
        for k,v in self.evaluated_vars.items():
            if v:   true_ev_vars.append(str(k))
            else:   false_ev_vars.append(str(k))

        ev_var_serialized = ','.join(true_ev_vars) + '-' + ','.join(false_ev_vars)       

        ### original_values
        original_values_serialized = str(self.original_values) 
    
        ### final_names_map
        final_names_map_serialized = str(self.final_names_map)

        return ev_var_serialized + '|' + original_values_serialized + '|' + final_names_map_serialized


    # when all clauses in a set get evaluated, then the set has a final value
    def set_value(self, val):
        self.value = val

    def add_clause(self, cl):
        # no need to add new clauses if the set is already evaluated previous to False
        if self.value == False:
            return

        if cl.value == False:
            self.set_value(False)
        elif cl.value == True and len(self.clauses) == 0:
            self.set_value(True)
        elif cl.value == None:
            self.clauses.append(cl)
            self.set_value(None)

        # if cl == True, then it has no meaning to add it

    def sort_within_clauses(self):
        for i in range(0, len(self.clauses)):
            self.clauses[i].sort()

    def sort_clauses(self):
        #self.clauses = sorted(self.clauses)

        def sort_by_var(cl):
            return abs(cl.raw[0])

        if len(self.clauses) > 0 and len(self.clauses[0].raw) > 0:
            self.clauses.sort()
        #self.clauses.sort()

    def rename_vars(self):
        # start from 1
        id = 1
        names_map = {}
        # keep track of the highest occurring var
        highest_occurring_vars_map = {}  
        for cl in self.clauses:
            for i in range(0, len(cl.raw)):
                sign = -1 if cl.raw[i] < 0 else 1
                new = names_map.get(abs(cl.raw[i]), None)
                if new == None:
                    new = id
                    names_map[abs(cl.raw[i])] = new
                    id = id + 1
                    
                cl.raw[i] = new * sign
                # calculate highest occurance var (should we count abs value?)
                highest_occurring_vars_map[cl.raw[i]] = highest_occurring_vars_map.get(cl.raw[i], 0) + 1
        
        self.highest_occurring_var = max(highest_occurring_vars_map, key=highest_occurring_vars_map.get)
        var_positions = list(names_map.keys())
        
        # if the set already gone through a round of rename before
        if self.final_names_map:
            self.final_names_map = [self.final_names_map[v-1] for v in var_positions]

        # if it's first round of rename, typically LOU mode has only one rename round per set
        else:
            self.final_names_map = var_positions

        self.sort_within_clauses()
        

    # l.o. state as in "Constructive patterns of logical truth", or "#2SAT is in P" p. 23:
        # 1- variables within clauses are in ascending order.
        # 2- clauses are in ascending ordered in the Set
        # 3- All new Names/Indices of literals occurring for the first time in any clause of S are strictly greater than all the Literal Names/Indices occurring before them in S.
        # 4- each clause is unique in the set. (this was already done on input parsing)
        # 5- the minimum literal id in the set equals MIN_LITERAL (new rule not in the paper). This is to force renaming if previous conditions are met but IDs start from a large value.
    #@param: mode:
        # lo (linearly ordered), all conditions are met
        # lou (linearly ordered universal), is a state where condition# 2 is skipped
        # normal: only condition 1 is met
    def is_in_lo_state(self, mode=MODE_LO):

        # condition 3
        if mode != MODE_NORMAL:
            seen_vars = {}
            if len(self.clauses) > 0 and len(self.clauses[0].raw) > 0:
                min_var = abs(self.clauses[0].raw[0])
                seen_vars[min_var] = True

                # condition 5 check
                if min_var > MIN_LITERAL:
                    logger.debug("Not in l.o.: min_var > MIN_LITERAL. min_var = {0}, MIN_LITERAL = {1}".format(min_var, MIN_LITERAL))
                    return False

                # condition 3
                for cl in self.clauses:
                    for var in cl.raw:
                        var = abs(var)
                        if var < min_var and not seen_vars.get(var, None):
                            logger.debug("Not in l.o.: var < min_var and not seen before. var = {0}, min_var = {1}".format(var, min_var))
                            return False

                        if not seen_vars.get(var, None):
                            seen_vars[var] = True
                            min_var = var

                # condition #2: is sorted?
                if mode != MODE_LOU:
                    min_var = abs(self.clauses[0].raw[0])
                    for cl in self.clauses:
                        var = abs(cl.raw[0])                            
                        if var < min_var:
                            return False
                        min_var = var

        return True

    # bring ONLY unit clauses to the far left (front of the set)
    def place_unit_clauses_first(self):
        
        def ShiftUnit(cl):
            if len(cl.raw) == 1:
                return -1
            return 1

        if len(self.clauses) > 0 and len(self.clauses[0].raw) > 0:
            self.clauses.sort(key=ShiftUnit)


    def sort_clauses_by_length(self):

        def clause_len(cl):
            return len(cl.raw)

        if len(self.clauses) > 0 and len(self.clauses[0].raw) > 0:
            self.clauses.sort(key=clause_len)

    
    def sort_clauses_by_len_and_initial_index(self):
        self.clauses.sort(key=lambda cl: (len(cl.raw), cl.initial_index))

    # convert to L.O. condition
    def to_lo_condition(self, mode=MODE_LO, sort_by_size=False, thief_method=False):
        
        # used in Thief method, sort by length,initial index
        if thief_method:
            self.sort_clauses_by_len_and_initial_index()

        if mode == MODE_FLOP or sort_by_size:
            # bring unit clauses to the front of the set
            # self.place_unit_clauses_first()
            self.sort_clauses_by_length()

        # rename
        self.rename_vars()
        # check L.O. conditions
        while not self.is_in_lo_state(mode):
            # condition 2
            if mode != MODE_LOU and mode != MODE_NORMAL:
                self.sort_clauses()
                if self.is_in_lo_state(mode):
                    break

            # rename
            self.rename_vars()
            

    # substitue the value of a var or more in the set.
    # vars map is a map of var name and value, such as {1: True, 2: False, 6: True}
    def substitute_vars(self, vars_map):
        vars = set(vars_map.keys())
        i = 0
        while i < len(self.clauses):
            cl = self.clauses[i]
            
            # does the clause has any of the evaluated vars?
            cl_vars = vars & set([abs(a) for a in cl.raw])
            
            if len(cl_vars) == 0:
                i += 1
                continue

            cl_popped = False
            clraw = list(cl.raw) # object copy
            for v in clraw:
                # if the clause evaluates to True, remove it
                if (abs(v) in cl_vars) and ((vars_map[abs(v)] == True and v > 0) or (vars_map[abs(v)] == False and v < 0)):
                    self.clauses.pop(i)
                    cl_popped = True
                    break
                elif abs(v) in cl_vars:
                    # for left branch, remove the var from the clause
                    cl.raw.pop(cl.raw.index(v))
                    if len(cl.raw) == 0:
                        # here it's unit clause that has a False value
                        cl.value = False

            if not cl_popped:
                i += 1

    # evaluate the set and produce two branches
    def evaluate(self):

        # sanity check
        if len(self.clauses) <= 0 or len(self.clauses[0].raw) <= 0: 
            return (None, None)

        # always pick the left most variable and evaluate based on it.
        pivot = abs(self.clauses[0].raw[0])
        #pivot = self.highest_occurring_var

        # Left Set: iterate through clauses, for each clause check if it has pivot, set it to True. If it has -pivot, remove the variable from the set
        # Right Set: opposite of left
        left_set = Set()
        right_set = Set()

        left_clauses = []
        right_clauses = []
        for c in self.clauses:
            cl = Clause(c.raw)
            cl.initial_index = c.initial_index
            # remove clause, i.e. set the var to true
            if pivot in cl.raw:
                # for left branch, the clause will be set to true. i.e. removed. (will not be added to left_clauses)
                
                # for right branch, remove the var from the clause
                cl.raw.pop(cl.raw.index(pivot))
                if len(cl.raw) > 0:
                    #ncl = Clause(cl.raw)
                    cl.substituted = True
                    right_clauses.append(cl)
                # if it's the last variable, then the clause will be evaluated to False, then all the Set will be False
                else:
                    right_set.set_value(False)
            # if it's negated, remove it from the clause and return the rest
            elif -pivot in cl.raw:
                # for right branch, the clause will be set to true. i.e. removed.

                # for left branch, remove the var from the clause
                cl.raw.pop(cl.raw.index(-pivot))
                if len(cl.raw) > 0:
                    cl.substituted = True
                    left_clauses.append(cl)
                # if it's the last variable, then the clause will be evaluated to False
                else:
                    left_set.set_value(False)

            else:
                lcl = Clause(cl.raw)
                lcl.initial_index = c.initial_index
                left_clauses.append(lcl)
                right_clauses.append(cl)
        
        
        left_set.clauses = left_clauses
        right_set.clauses = right_clauses

        if len(left_clauses) == 0 and left_set.value == None:
            left_set.set_value(True)

        if len(right_clauses) == 0 and right_set.value == None:
            right_set.set_value(True)


        # set a map to the original variables in each set
        for sset in (left_set, right_set):
            vars = sset.get_variables()
            sset.original_values = {v:self.original_values[self.final_names_map[v-1]] for v in vars}

        left_set.evaluated_vars = {**self.evaluated_vars, self.original_values[self.final_names_map[abs(pivot)-1]]:True}
        right_set.evaluated_vars = {**self.evaluated_vars, self.original_values[self.final_names_map[abs(pivot)-1]]:False}

        return (left_set, right_set)


    def to_string(self, pretty=True, only_evaluated_clauses=False):

        # if the set evaluates to a value
        if self.value != None:
            res = str(self.value)[0]
            return res

        # This shouldn't ever happen. If the set doesn't have a value, then it must has clauses
        if len(self.clauses) == 0:
            raise ValueError('A set with empty clauses and no evaluated values!')

        res_arr = []
        for cl in self.clauses:
            if len(cl.raw):
                if only_evaluated_clauses and not cl.substituted:
                    continue

                if pretty:
                    res_arr.append('(' + ' | '.join(map(str, cl.raw)) + f')[{cl.initial_index}]')
                else:                    
                    res_arr.append('|'.join(map(str, cl.raw)))

        if pretty:
            res = ' & '.join(res_arr)
        else:
            res = '&'.join(res_arr)
            
        return res

    
    # return a list of variables in the set
    def get_variables(self):
        vars = set()
        for cl in self.clauses:
            vars |= set(map(abs, cl.raw))

        return list(vars)

    @staticmethod
    def calculate_hash(input_str):
        # sha1 hash
        return hashlib.sha1(bytes(input_str, "ascii")).digest() 
        
    def get_hash(self, force_recalculate=False):
        if self.computed_hash == None or force_recalculate:
            self.computed_hash = Set.calculate_hash(self.to_string(pretty=False))
        return self.computed_hash

    def print_set(self):
        print(self.to_string())
    
    @staticmethod
    def get_true_set_hash():
        return Set.calculate_hash('T')
    
    @staticmethod
    def get_false_set_hash():
        return Set.calculate_hash('F')
