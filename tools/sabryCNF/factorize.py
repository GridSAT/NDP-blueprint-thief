import sys
import math
import time

def factorize(x):

    sq = math.sqrt(x)
    for i in range(3, int(sq+1), 2):
        if x % i == 0:
            return i

    return f'The number {x} is Prime!'



x = int(sys.argv[1])

start_time = time.time()
fact1 = factorize(x)
fact2 = int(x/fact1)


print(f"{x} = {fact1} x {fact2} .. verified = {x == (fact1 * fact2)}")

# Complexity calculation
# if x is n-bit number, then runtime complexity of the loop is sqrt(x) = O(2^(n/2))
# in each iteration, we divide x by a number i where 3 <= i <= sqrt(x)
# each divide operation has O(n * m) using naive algorithm, where m is number of bits of i
# so total complexity is O(2^(n/2) nm)

#print(f"input's sqrt = {math.ceil(math.sqrt(x))}, sqrt bits = {math.ceil(math.log2(x)/2)}")
n = math.ceil(math.log2(x))

# m could be also n/2 for upper bound, but here I calculate it on lower bound
m = n/2 #math.ceil(math.log2(math.sqrt(x)))
max_complexity = int((2 ** (n/2)) * (n * m))
# assuming SRT division complexity nlogn
min_complexity = int((2 ** (n/2)) * math.log2(n))
print(f'Brute force max steps = {max_complexity:,}')
print(f'Brute force w SRT div = {min_complexity:,}')
#print(f'Best heuristic algorithm= {math.ceil(2 ** ( (n ** (1/3)) * (math.log2(n) ** (2/3)) ))}')
#print(f'Best fully proven algorithm = {math.ceil(2 ** (math.sqrt(n * math.log2(n))))}')
#print(f'max steps2 = {math.sqrt(x) * (n * math.ceil(math.log2(math.sqrt(x))))}')
print('script took %.3f seconds' % (time.time() - start_time))