#!/bin/bash

#echo "########## experiment 8 ##########" >> result-experiment-8
#echo "########## TRACE=50, REDUCE=False ##########"
#echo "########## TRACE=50, REDUCE=False ##########" >> result-experiment-8
#(gtime python3.12 ../../poet.py --property=property.pctl --trace=traces/trace-50.json --output-level=max_state --log-categories="") >> result-experiment-8 2>&1

echo "########## TRACE=50, REDUCE=True ##########"
echo "########## TRACE=50, REDUCE=True ##########" >> result-experiment-8
(gtime python3.12 ../../poet.py --property=property.pctl --trace=traces/trace-50.json --reduce --output-level=max_state --log-categories="") >> result-experiment-8 2>&1

#echo "########## TRACE=100, REDUCE=False ##########"
#echo "########## TRACE=100, REDUCE=False ##########" >> result-experiment-8
#(gtime python3.12 ../../poet.py --property=property.pctl --trace=traces/trace-100.json --output-level=max_state --log-categories="") >> result-experiment-8 2>&1

echo "########## TRACE=100, REDUCE=True ##########"
echo "########## TRACE=100, REDUCE=True ##########" >> result-experiment-8
(gtime python3.12 ../../poet.py --property=property.pctl --trace=traces/trace-100.json --reduce --output-level=max_state --log-categories="") >> result-experiment-8 2>&1

#echo "########## TRACE=500, REDUCE=False ##########"
#echo "########## TRACE=500, REDUCE=False ##########" >> result-experiment-8
#(gtime python3.12 ../../poet.py --property=property.pctl --trace=traces/trace-500.json --output-level=max_state --log-categories="") >> result-experiment-8 2>&1

echo "########## TRACE=500, REDUCE=True ##########"
echo "########## TRACE=500, REDUCE=True ##########" >> result-experiment-8
(gtime python3.12 ../../poet.py --property=property.pctl --trace=traces/trace-500.json --reduce --output-level=max_state --log-categories="") >> result-experiment-8 2>&1

#echo "########## TRACE=1000, REDUCE=False ##########"
#echo "########## TRACE=1000, REDUCE=False ##########" >> result-experiment-8
#(gtime python3.12 ../../poet.py --property=property.pctl --trace=traces/trace-1000.json --output-level=max_state --log-categories="") >> result-experiment-8 2>&1

echo "########## TRACE=1000, REDUCE=True ##########"
echo "########## TRACE=1000, REDUCE=True ##########" >> result-experiment-8
(gtime python3.12 ../../poet.py --property=property.pctl --trace=traces/trace-1000.json --reduce --output-level=max_state --log-categories="") >> result-experiment-8 2>&1