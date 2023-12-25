#	Multiply.py
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

class Multiply:
    def __init__(self) -> None:
        pass

    # This preprocessing method is ONLY for multiplication CNFs generated by Paul Purdom and Amr Sabry at https://cgi.luddy.indiana.edu/~sabry/cnf.html
    # The task multiplies two numbers using the input CNF. It is irrelevant if the CNF was generated for a specific number of bit-length n.
    # What matters is that we can use the CNF as a processor to multiply two numbers and produce a number x of length n
    
    def preprocess_set(self, cnf: Set, fact1, fact2):
        # compatibility check
        if not (cnf and len(cnf.clauses) and len(cnf.clauses[0].raw) == 3):
            print("The input set is not in Purdom-Sabry format. Multiplication feature skipped.")
            return False

        vars_map = {}

        ### evaluate the two input factors/multipliers
        # first get the size of each factor
        # length of factor1 and factor 2 are in first clause
        cnf.fact1_len = cnf.clauses[0].raw[1]-1
        cnf.fact2_len = abs(cnf.clauses[0].raw[2]) - cnf.clauses[0].raw[1]

        # get fact1 var to have the bigger value
        if fact2 > fact1:
            fact1, fact2 = fact2, fact1
        
        # check if input factors are bigger than the factors' bits in the CNF
        fact1bin = bin(fact1)[2:].rjust(cnf.fact1_len, '0')[::-1]
        fact2bin = bin(fact2)[2:].rjust(cnf.fact2_len, '0')[::-1]
        if len(fact1bin) > cnf.fact1_len or len(fact2bin) > cnf.fact2_len:
            print("The tree is not compatible. One or both factors are greater than factors assigned bits in the tree.")
            return False

        vars_map = {}
        i = 1
        for factbin, flen in [(fact1bin, cnf.fact1_len), (fact2bin, cnf.fact2_len)]:
            for bit in factbin:
                vars_map[i] = bool(int(bit))
                i += 1

        # The size of the output number in bits equal number of unit clauses
        result_bits = []
        for i in range(len(cnf.clauses) - 1, -1, -1):
            cl = cnf.clauses[i]
            if len(cl.raw) == 1:
                result_bits.append(abs(cl.raw[0]))

                # remove unit clauses to make the CNF be a general CNF for all results within the N-bit range
                cnf.clauses.pop(i)

        cnf.multiply_result_bits = result_bits[::-1]
        cnf.evaluated_vars = vars_map

        cnf.substitute_vars(vars_map)
        
        return True
