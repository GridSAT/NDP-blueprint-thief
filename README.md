README.md

Non-Deterministic Processor (NDP) - efficient parallel SAT-solver
Copyright (c) 2023 GridSAT Stiftung

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

GridSAT Stiftung - Georgstr. 11 - 30159 Hannover - Germany - ipfs: gridsat.eth/ - info@gridsat.io



### Concept:

NDP is the abbreviation for [Non-Deterministic Processor](https://en.wikipedia.org/wiki/Nondeterministic_Turing_machine).
One of the most important questions in theoretical computer science was the [P vs. NP problem](https://en.wikipedia.org/wiki/P_vs._NP_problem) asking how difficult it is to simulate non-deterministic computation with a deterministic computer.
The class NP represented problems with no known polynomial-time solution, but if given a solution, it was verifiable to be correct within polynomial time.
It was called non-deterministic polynomial because a non-deterministic machine could solve it in polynomial time.
NP problems were beyond computability, incl. but not limited to quantum computation which [itself](https://www.nature.com/articles/s41534-017-0035-1.pdf) is [NP-complete](https://iopscience.iop.org/article/10.1088/1367-2630/16/3/033027/pdf).


### Impact:

An NDP makes the [whole internet look like a footnote in history](https://www.researchgate.net/publication/220423686_The_Status_of_the_P_versus_NP_problem).
It may be [as important as the discovery of fire](https://youtu.be/kiL-xAGQ8yQ).


### Implementation:

The NDP solves any NP problem in polynomial time with [unlimited linear scalability](https://youtu.be/ldbW_PuYd6w) over multi-core deployments.
Just as any other processor, it computes deterministically.
It processes problems formulated in [SAT](https://en.wikipedia.org/wiki/Boolean_satisfiability_problem) (3SAT) transformed into [CNF (DIMACS)](https://jix.github.io/varisat/manual/0.2.0/formats/dimacs.html) outputting the [most fundamental data structure](https://youtu.be/SQE21efsf7Y) in computer science called Binary Decision Diagrams (BDD).
BDDs are as fundamental as .txt files for word processors.


### Theoretical background:

Recalling that BDDs are graph representations of boolean functions with with 2^n+1 -1 nodes being equivalent to the complete [truth table](https://en.wikipedia.org/wiki/Truth_table), we can collapse the tree in such a way, that the function can still be evaluated in the same manner, yet the resulting acyclic digraph (BDD) may be much smaller.
Accordingly [it is known and has been severally demonstrated](http://alumni.cs.ucr.edu/~skulhari/StaticHeuristics.pdf), that the variable ordering of the respective input set can significantly impact the size of a BDD (i.e., the efficiency of generating the BDD). 
The variable ordering problem can therefore be viewed as determining a permutation of the input variables that provides the sequence representing these implicants efficiently and keeping the size of the resulting BDD minimal.

However it is further known, that finding an [optimal variable order is NP-complete](https://ieeexplore.ieee.org/document/537122) and that OBDD lower bounds for some special functions seemed to be exponential [independant of any variable ordering](https://www.researchgate.net/publication/3042737_On_the_complexity_of_VLSI_implementations_and_graph_representationsof_Boolean_functions_with_application_to_integer_multiplication).

Non-withstanding of these OBDD functions, the NDP bypasses those exponential lower bounds through [equisatisfiable translations](https://en.wikipedia.org/wiki/Equisatisfiability) enabling BDD sizes approximated by O(M^4), where M is the number of clauses of a CNF representation of the function. The average case fittings for FACT and MULT are even much more efficient when generating the CNF-input with [Paul Purdom and Amr Sabry ’s transformation](https://cgi.luddy.indiana.edu/~sabry/cnf.html). 


### History:

[Algebra was introduced some 1,200 years ago](https://en.wikipedia.org/wiki/Muhammad_ibn_Musa_al-Khwarizmi#Algebra). In [classic Arabic](https://www.ted.com/talks/terry_moore_why_is_x_the_unknown?utm_campaign=tedspread&utm_medium=referral&utm_source=tedcomshare) with [Arabic numerals](https://en.wikipedia.org/wiki/Arabic_numerals) in addition to 0 introduced from the [Hindu numeral system](https://en.wikipedia.org/wiki/Hindu–Arabic_numeral_system).
While todays [elementary algebra](https://en.wikipedia.org/wiki/Elementary_algebra) symbolizes variables with Latin letters whose values are Arabic numbers, [Boolean algebra](https://en.wikipedia.org/wiki/Boolean_algebra) only assigns true and false values, usually denoted 1 and 0 to the respective letter, e.g., X. Furthermore, subject matter Boolean functions in CNF use the logical and operator (often denoted as ∧) and the negation not (often denoted as ¬).
Accordingly, a Boolean function contains variables and logical connectors representing its form (syntax). The meaning (semantic) of that Boolean function is represented by the ordered set of variable value combinations, i.e., by its truth table.


### The Magic:

The relation between syntax and semantics in formal and natural languages is one of the [most debated topics in modern logics and linguistics](https://plato.stanford.edu/entries/linguistics/). Its understanding bears important consequences for both, computer science and computational linguistics.
Fundamental doctrines of logic ([Frege](https://en.wikipedia.org/wiki/Gottlob_Frege), [Russell](https://en.wikipedia.org/wiki/Bertrand_Russell), [Tarski](https://en.wikipedia.org/wiki/Alfred_Tarski) and their followers) assume that symbols refer solely to things of the world and that reference to those things is uniquely determined by the context of a sentence, but not by any intrinsic features of the used symbols.

[Classic Arabic is known to contradict those doctrines](https://oxfordre.com/literature/display/10.1093/acrefore/9780190201098.001.0001/acrefore-9780190201098-e-989?rskey=XbsfVv&result=1): Symbols refer to meanings but not to things. Meanings are embedded in the permutations of characters used in the symbols. Thus, a symbol contains its own independent semantic nuance, which is only complemented by the context of usage. 

Putting this feature of classic Arabic into action for SAT processing reveals semantic patterns hidden behind names of variables used in CNF formulas. E.g., if indices in variable names reflect repetition lengths of 0 and 1 patterns in the truth table, it can be shown that inducing a linear order between those indices by means of simple renaming, always enables construction of small BDDs.

Please check the [Resources](https://gridsat.eth.link/resources.html) on this site for a comprehensive and authentic overview.



### Non-Deterministic Processor (NDP) blueprint with Ray

### Installation

##### Prepare system virtualenv

On linux run as root

```bash
apt install python3-pip libpq-dev sysstat
```

##### Create virtualenv

Log-in as user and run

```bash
cd <path_to_directory>

virtualenv <dir_name>
```

### Activate and update virtualenv

Login as user and run

```bash
cd <path_to_directory>

source <dir_name>/bin/activate

pip install -r requirements.txt
```

### Install Ray

https://github.com/ray-project/ray


### Startup the RAY nodes to allow multi-processing on cluster

Using [ray](https://docs.ray.io) for upscaling the showcase.

The installation is already done after pip install from previous steps


##### Start head node

```bash
export RAY_DISABLE_IMPORT_WARNING=1
CPUS=$(( $(lscpu --online --parse=CPU | egrep -v '^#' | wc -l) - 4 ))
ray start --head --include-dashboard=false --num-gpus=0 --num-cpus=$CPUS
```

##### Start additional nodes

```bash
export RAY_DISABLE_IMPORT_WARNING=1
CPUS=$(( $(lscpu --online --parse=CPU | egrep -v '^#' | wc -l) - 4 ))
ray start --include-dashboard=false --address='MASTER-IP:6379' --redis-password='MASTER-PASSWORT' --num-gpus=0 --num-cpus=$CPUS
```

To add more worker nodes just run same on additional nodes



### Run solver (e.g. DIMACS format with l.o.u. condition in verbos on 8 cores)

```bash
python3 main.py -v -d inputs/[CNF/DIMACS] -m lou -t 8
```

### Run solver for FACT most efficiently, e.g., [DIMACS-Sabry input](https://cgi.luddy.indiana.edu/~sabry/cnf.html) with l.o.u. condition and thief-method in verbos on 8 cores)

```bash
python3 main.py -v -d inputs/[CNF/DIMACS in Sabry-format] -m lou -thief -t 8
```

The main process connects automatically to the head node and uses workers as available.



### Starter tools

Some helpers to easily run the processes and environments (e.g. AWS):

```bash

# .bin/ray.sh
sudo su - [user_name]

# .bin/ray-auto.sh
sudo -u [user_name] -i /bin/bash -i -c ray-auto.sh

# .bin/node.sh
ssh -i $HOME/.ssh/AWS.pem "node$1"

# .bin/node-up.sh
ssh -i $HOME/.ssh/AWS.pem "node$1" -t .bin/ray-auto.sh

# run and log unbuffered (need expect-dev installed)
CORES="0001"; BITS="14"; ( echo "START: `date`"; echo ""; unbuffer python3 main.py -v -d inputs/Multi"$BITS"bit.txt -m lou -t $CORES 2>/dev/null ; echo "" ; echo "ENDE: `date`" ) | tee logs/$(date "+%Y-%m-%d")_Multi"$BITS"bit-$CORES-Cores.txt

# run and start on [HEADNODE]
cd $HOME/myDirectory; source __venv__/bin/activate ; PATH=$PATH:/home/myDirectory/bin ray-auto.sh [HEADNODE] 8

# run and start on a [NODE]
cd $HOME/myDirectory; source __venv__/bin/activate ; PATH=$PATH:/home/myDirectory/bin ray-auto.sh [NODE] 22

```
