λ python main.py -d inputs\test_cases\Factoring80.txt
Execution finished!
Input set processed in 9916.755 seconds
Total number of unique nodes: 1742939
Total number of redundant subtrees: 7864
Total number of nodes in a complete binary tree for the problem: 4194303
Current memory usage: 2.5GiB
script took 9916.760 seconds

λ python main.py -d inputs\test_cases\Factoring80.txt -lou
Execution finished!
Input set processed in 168.486 seconds
Total number of unique nodes: 32549
Total number of redundant nodes: 263
Total number of nodes in a complete binary tree for the problem: 65535
Current memory usage: 131.2MiB
script took 168.500 seconds


# the previous flag of -lou, is what equivalent now to -m lo. Thus, don't think the follow -m is equivalent to the mode in the previous result
λ python main.py -d inputs\test_cases\Factoring80.txt -m lou
Execution finished!
Input set processed in 180.481 seconds
Solution mode: lou
Total number of unique nodes: 22931
Total number of redundant subtrees: 298
Total number of nodes in a complete binary tree for the problem: 65535
Current memory usage: 115.8MiB
script took 180.486 seconds