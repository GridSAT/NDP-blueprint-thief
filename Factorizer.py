#	Factorizer.py
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

from Clause import Clause
from Set import Set

class Factorizer:
    def __init__(self) -> None:
        pass

    # This preprocessing method is ONLY for factorization CNFs generated by Paul Purdom and Amr Sabry at https://cgi.luddy.indiana.edu/~sabry/cnf.html
    def preprocess_set(self, cnf: Set):
        # compatibility check
        if not (cnf and len(cnf.clauses) and len(cnf.clauses[0].raw) == 3):
            print("The input set is not in Purdom-Sabry format. Factorization feature skipped.")
            return False

        vars_map = {}
        # evaluate unit clauses (the output in Purdom-Sabry format)
        # unit clauses are in order, first is the lsb of the output value

        factorized_number = 0
        i = 0
        for cl in cnf.clauses:
            if len(cl.raw) == 1:
                v = cl.raw[0]
                # store the value of the variable
                vars_map[abs(v)] = v > 0
                # calculate the value of the input number
                factorized_number += int(v > 0) * 2**i
                i += 1
        
        cnf.factorized_number = factorized_number
        
        # the length in bits of the input number of factorization problem
        cnf.fact_num_bits = list(vars_map.keys())

        # length of factor1 and factor 2 are in first clause
        cnf.fact1_len = cnf.clauses[0].raw[1]-1
        cnf.fact2_len = abs(cnf.clauses[0].raw[2]) - cnf.clauses[0].raw[1]

        # If the factorized number is odd, then we know for sure that both its factors are odd
        # we can use this information to set the lsb of both factors to 1
        if cnf.factorized_number % 2:
            vars_map[1] = True
            vars_map[cnf.fact1_len+1] = True
        
        cnf.evaluated_vars = vars_map
        cnf.substitute_vars(vars_map)
        return True
