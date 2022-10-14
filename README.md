<!--
#	README.md
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

#	GridSAT Stiftung - Georgstr. 11 - 30159 Hannover - Germany - info@gridsat.io
#
-->

### Installation

##### Prepare system virtual environment (virtualenv)

On linux run as root

```bash
apt install python3-pip libpq-dev
```

##### Create virtual environment (virtualenv)

Log-in as user and run

```bash
cd /path/pattern_solvers

virtualenv pattern_solvers
```


### Activate and update virtual environment (virtualenv)

Login as user and run

```bash
cd /path/pattern_solvers

source pattern_solvers/bin/activate

pip install -r requirements
```


### Run solver

```bash
python3 main.py -v -d inputs/Multi11bit.txt -m lou -t 8
```
