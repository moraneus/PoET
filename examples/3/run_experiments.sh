#!/bin/bash

echo "########## spec 3 ##########" >> result-spec-3

echo "########## TRACE=50, REDUCE=False ##########"
echo "########## TRACE=50, REDUCE=False ##########" >> result-spec-3
(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-50.json --experiment) >> result-spec-3 2>&1

echo "########## TRACE=50, REDUCE=True ##########"
echo "########## TRACE=50, REDUCE=True ##########" >> result-spec-3
(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-50.json --reduce --experiment) >> result-spec-3 2>&1

echo "########## TRACE=100, REDUCE=False ##########"
echo "########## TRACE=100, REDUCE=False ##########" >> result-spec-3
(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-100.json --experiment) >> result-spec-3 2>&1

echo "########## TRACE=100, REDUCE=True ##########"
echo "########## TRACE=100, REDUCE=True ##########" >> result-spec-3
(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-100.json --reduce --experiment) >> result-spec-3 2>&1

echo "########## TRACE=500, REDUCE=False ##########"
echo "########## TRACE=500, REDUCE=False ##########" >> result-spec-3
(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-500.json --experiment) >> result-spec-3 2>&1

echo "########## TRACE=500, REDUCE=True ##########"
echo "########## TRACE=500, REDUCE=True ##########" >> result-spec-3
(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-500.json --reduce --experiment) >> result-spec-3 2>&1

echo "########## TRACE=1000, REDUCE=False ##########"
echo "########## TRACE=1000, REDUCE=False ##########" >> result-spec-3
(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-1000.json --experiment) >> result-spec-3 2>&1

echo "########## TRACE=1000, REDUCE=True ##########"
echo "########## TRACE=1000, REDUCE=True ##########" >> result-spec-3
(gtime python3.12 ../../poet.py --property=property --trace=traces/trace-1000.json --reduce --experiment) >> result-spec-3 2>&1
