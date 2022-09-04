#!/bin/bash

# if [[ $# -eq 0 ]] ; then
#     echo 'some message'
#     exit 0
# fi

# case "$1" in
#     1) echo 'you gave 1' ;;
#     *) echo 'you gave something else' ;;
# esac

if [ "$1" = "" ] || [ "$2" = "" ]
    then
    echo "Please provide [num1] [num2] for range of numbers to generate."
    exit 0

fi

# if multiple numbers are given as input
if [[ $# -gt 2 ]] ; then
    for i in $@
    do
        echo "Generating CNF for $i"
        ./sabry_cnf_gen $i n-bit wallace > "../inputs/test_cases/Benchmarks/Factoring$i.txt"
    done
    exit 0
fi

# if two numbers only are given as range 
for ((i=$1;i<=$2;i++))
do
    echo "Generating CNF for $i"
   ./sabry_cnf_gen $i n-bit wallace > "../inputs/test_cases/Benchmarks/Factoring$i.txt"
done
