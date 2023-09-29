#	Clause.py
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

class Clause:
    
    def __init__(self, inp):
        self.raw = []
        self.value = None
        self.substituted = False # a flag set to true if a var in this clause is substituted with a bool value
        self.initial_index = 0

        if type(inp) is list or type(inp) is frozenset:
            self.raw = list(inp)
            self.sort()

            # handle case of (x, -x), since the array is sorted, then same element with different sign will be adjacent
            if len(self.raw) >= 2:
                if abs(self.raw[0]) == abs(self.raw[1]):
                    self.value = True
                    self.raw = []

            if len(self.raw) == 3:
                if abs(self.raw[1]) == abs(self.raw[2]):
                    self.value = True
                    self.raw = []

        elif type(inp) is bool:
            self.value = inp
        
    def __lt__(self, other):
        shortlen = min(len(self.raw), len(other.raw))
               
        # case where both are of equal length
        for i in range(0, shortlen):

            if self.raw[i] == other.raw[i]:
                continue

            # only if two number with different signs, ex. -5 and 5, are compared, consider +5 is less
            if self.raw[i] != other.raw[i] and abs(self.raw[i]) == abs(other.raw[i]):
                return self.raw[i] > other.raw[i]
            
            # do absolute value comparison, so that -5 is greater than 3, for example.
            return abs(self.raw[i]) <= abs(other.raw[i])

        # in case both are identical values up until shortlen, then put the shorter first
        return len(self.raw) < len(other.raw)
    

    def sort(self):
        x = sorted(self.raw, key = abs)
        self.raw = x
