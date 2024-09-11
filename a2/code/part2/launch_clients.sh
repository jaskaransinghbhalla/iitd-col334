#!/bin/bash

num_clients=5

for i in $(seq 1 $num_clients)
do
    ./client $i &
done

wait