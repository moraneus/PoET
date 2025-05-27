#!/bin/bash

echo "########## experiment 1 ##########" >> result-experiment-1

#echo "########## TRACE=1K, REDUCE=False ##########"
#echo "########## TRACE=1K, REDUCE=False ##########" >> result-experiment-1
#(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-1K.json --output-level=max_state) >> result-experiment-1 2>&1

echo "########## TRACE=1K, REDUCE=True ##########"
echo "########## TRACE=1K, REDUCE=True ##########" >> result-experiment-1
(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-1K.json --reduce --output-level=max_state) >> result-experiment-1 2>&1

#echo "########## TRACE=10K, REDUCE=False ##########"
#echo "########## TRACE=10K, REDUCE=False ##########" >> result-experiment-1
#(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-10K.json --output-level=max_state) >> result-experiment-1 2>&1

echo "########## TRACE=10K, REDUCE=True ##########"
echo "########## TRACE=10K, REDUCE=True ##########" >> result-experiment-1
(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-10K.json --reduce --output-level=max_state) >> result-experiment-1 2>&1

#echo "########## TRACE=100K, REDUCE=False ##########"
#echo "########## TRACE=100K, REDUCE=False ##########" >> result-experiment-1
#(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-100K.json --output-level=max_state) >> result-experiment-1 2>&1

echo "########## TRACE=100K, REDUCE=True ##########"
echo "########## TRACE=100K, REDUCE=True ##########" >> result-experiment-1
(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-100K.json --reduce --output-level=max_state) >> result-experiment-1 2>&1

#echo "########## TRACE=500K, REDUCE=False ##########"
#echo "########## TRACE=500K, REDUCE=False ##########" >> result-experiment-1
#(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-500K.json --output-level=max_state) >> result-experiment-1 2>&1

echo "########## TRACE=500K, REDUCE=True ##########"
echo "########## TRACE=500k, REDUCE=True ##########" >> result-experiment-1
(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-500K.json --reduce --output-level=max_state) >> result-experiment-1 2>&1
