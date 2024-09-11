#!/bin/bash
# output file csv
scores_path='../data/scores.csv'
student_submission_path_dir='../submissions'
ta_submission_path_dir='../solution'
num_clients=2
config_file_part1='./testcases/config_1.json'
config_file_part2='./testcases/config_2.json'
config_file_part3='./testcases/config_3.json'
config_file_part4='./testcases/config_4.json'
test_case='./testcases/input_543.txt'
output='./testcases/output_543.txt'

# scores
declare -A scores
declare -A execution_times
declare -A plots
declare -A jains_fairness_index
pattern='^20[A-Za-z0-9]{9}_20[A-Za-z0-9]{9}\.zip$'

execution_times=(
    [part1_time]=10
    [part2_time]=10
    [part3_time]=10
    [part4_time]=10
    [cross_verification_ta_server_student_client_part1_time]=10
    [cross_verification_ta_server_student_client_part2_time]=10
    [cross_verification_ta_server_student_client_part3_aloha_time]=10
    [cross_verification_ta_server_student_client_part3_beb_time]=10
    [cross_verification_ta_server_student_client_part3_cscd_time]=10
    [cross_verification_ta_server_student_client_part4_fifo_time]=10
    [cross_verification_ta_server_student_client_part4_rr_time]=10
    [cross_verification_student_server_ta_client_part1_time]=10
    [cross_verification_student_server_ta_client_part2_time]=10
    [cross_verification_student_server_ta_client_part3_aloha_time]=10
    [cross_verification_student_server_ta_client_part3_beb_time]=10
    [cross_verification_student_server_ta_client_part3_cscd_time]=10
    [cross_verification_student_server_ta_client_part4_fifo_time]=10
    [cross_verification_student_server_ta_client_part4_rr_time]=10
)

scores=(
    [part1]=0
    [part2]=0
    [part3_aloha]=0
    [part3_beb]=0
    [part3_cscd]=0
    [part4_fifo]=0
    [part4_rr]=0
    [cross_verification_ta_server_student_client_part1]=0
    [cross_verification_ta_server_student_client_part2]=0
    [cross_verification_ta_server_student_client_part3_aloha]=0
    [cross_verification_ta_server_student_client_part3_beb]=0
    [cross_verification_ta_server_student_client_part3_cscd]=0
    [cross_verification_ta_server_student_client_part4_fifo]=0
    [cross_verification_ta_server_student_client_part4_rr]=0
    [cross_verification_student_server_ta_client_part1]=0
    [cross_verification_student_server_ta_client_part2]=0
    [cross_verification_student_server_ta_client_part3_aloha]=0
    [cross_verification_student_server_ta_client_part3_beb]=0
    [cross_verification_student_server_ta_client_part3_cscd]=0
    [cross_verification_student_server_ta_client_part4_fifo]=0
    [cross_verification_student_server_ta_client_part4_rr]=0
    [total]=0
)

plots=(
    [part1]='../data/part1'
    [part2]='../data/part2'
    [part3]='../data/part3'
    [part4]='../data/part4'
)

jains_fairness_index=(
    [part4]='../data/part4_jains_fairness_index'
)

mkdir -p ../temp
mkdir -p ../data/part1
mkdir -p ../data/part2
mkdir -p ../data/part3
mkdir -p ../data/part4
mkdir -p ../data/part4_jains_fairness_index

part1_plot_execution_time_extraction() {
    local entry_num1=$1
    local entry_num2=$2
    cp "$test_case" ../temp/part1/testcase.txt
    cp "$config_file_part1" ../temp/part1/config.json
    temp_file=$(mktemp)
    make -C ../temp/part1 build >> log.txt 2>&1
    { time make -C ../temp/part1 run >> log.txt 2>&1 ; } 2> "$temp_file"
    part1_time=$(grep '^user' "$temp_file" | awk '{print $2}')
    make -C ../temp/part1 plot >> log.txt 2>&1
    cp ../temp/part1/plot.png "${plots[part1]}/$entry_num1.png"
    cp ../temp/part1/plot.png "${plots[part1]}/$entry_num2.png"
    execution_times[part1_time]=$part1_time
    if [ -f ../temp/part1/plot.png ]; then
        scores[part1]=$((scores[part1] + 1))
    fi
    rm "$temp_file"
    rm ../temp/part1/testcase.txt
}

part2_plot_execution_time_extraction(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$test_case" ../temp/part2/testcase.txt
    cp "$config_file_part2" ../temp/part2/config.json
    temp_file=$(mktemp)
    make -C ../temp/part2 build >> log.txt 2>&1
    { time make -C ../temp/part2 run >> log.txt 2>&1; } 2> "$temp_file"
    part2_time=$(grep '^user' "$temp_file" | awk '{print $2}')
    make -C ../temp/part2 plot >> log.txt 2>&1
    cp ../temp/part2/plot.png "${plots[part2]}/$entry_num1.png"
    cp ../temp/part2/plot.png "${plots[part2]}/$entry_num2.png"
    execution_times[part2_time]=$part2_time
    if [ -f ../temp/part2/plot.png ]; then
        scores[part2]=$((scores[part2] + 1))
    fi
    rm "$temp_file"
    rm ../temp/part2/testcase.txt
}

part3_plot_execution_time_extraction(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$test_case" ../temp/part3/testcase.txt
    cp "$config_file_part3" ../temp/part3/config.json
    temp_file=$(mktemp)
    make -C ../temp/part3 build >> log.txt 2>&1
    { time make -C ../temp/part3 run >> log.txt 2>&1; } 2> "$temp_file"
    part3_time=$(grep '^user' "$temp_file" | awk '{print $2}')
    make -C ../temp/part3 plot >> log.txt 2>&1
    cp ../temp/part3/plot.png "${plots[part3]}/$entry_num1.png"
    cp ../temp/part3/plot.png "${plots[part3]}/$entry_num2.png"
    execution_times[part3_time]=$part3_time
    if [ -f ../temp/part3/plot.png ]; then
        scores[part3_aloha]=$((scores[part3_aloha] + 1))
        scores[part3_beb]=$((scores[part3_beb] + 1))
        scores[part3_cscd]=$((scores[part3_cscd] + 1))
    fi
    rm "$temp_file"
    rm ../temp/part3/testcase.txt
}

part4_plot_execute_time_fairness_extraction(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$test_case" ../temp/part4/testcase.txt
    cp "$config_file_part4" ../temp/part4/config.json
    temp_file=$(mktemp)
    make -C ../temp/part4 build >> log.txt 2>&1
    { time make -C ../temp/part4 run >> log.txt 2>&1; } 2> "$temp_file"
    part4_time=$(grep '^user' "$temp_file" | awk '{print $2}')
    make -C ../temp/part4 plot >> log.txt 2>&1
    cp ../temp/part4/plot.png "${plots[part4]}/$entry_num1.png"
    cp ../temp/part4/plot.png "${plots[part4]}/$entry_num2.png"
    execution_times[part4_time]=$part4_time
    cp ../temp/part4/jains_fairness_index.txt "${jains_fairness_index[part4]}/$entry_num1.txt"
    cp ../temp/part4/jains_fairness_index.txt "${jains_fairness_index[part4]}/$entry_num2.txt"
    if [ -f ../temp/part4/plot.png ]; then
        scores[part4_fifo]=$((scores[part4_fifo] + 1))
        scores[part4_rr]=$((scores[part4_rr] + 1))
    fi
    if [ -f ../temp/part4/jains_fairness_index.txt ]; then
        scores[part4_fifo]=$((scores[part4_fifo] + 1))
        scores[part4_rr]=$((scores[part4_rr] + 1))
    fi
    rm "$temp_file"
    rm ../temp/part4/testcase.txt
}


cross_verification_student_server_ta_client_part1(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$test_case" ../temp/part1/testcase.txt
    cp "$config_file_part1" ../temp/part1/config.json
    temp_file=$(mktemp)
    { time make -C ../temp/part1 server >> log.txt 2>&1; } 2> "$temp_file"
    make -C "$ta_submission_path_dir/part1" client >> log.txt 2>&1
    execution_times[cross_verification_student_server_ta_client_part1_time]=$(grep '^user' "$temp_file" | awk '{print $2}')
    rm "$temp_file"
    rm ../temp/part1/testcase.txt
    for i in $(seq 1 1); do
        if diff -q "$output" "$ta_submission_path_dir/part1/client_$i.txt"; then
            scores[cross_verification_student_server_ta_client_part1]=$((scores[cross_verification_student_server_ta_client_part1] + 1))
        fi
    done
}

cross_verification_student_server_ta_client_part2(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$test_case" ../temp/part2/testcase.txt
    cp "$config_file_part2" ../temp/part2/config.json
    temp_file=$(mktemp)
    { time make -C ../temp/part2 server >> log.txt 2>&1; } 2> "$temp_file"
    make -C "$ta_submission_path_dir/part2" client >> log.txt 2>&1
    execution_times[cross_verification_student_server_ta_client_part2_time]=$(grep '^user' "$temp_file" | awk '{print $2}')
    rm "$temp_file"
    rm ../temp/part2/testcase.txt
    for i in $(seq 1 $num_clients); do
        if diff -q "$output" "$ta_submission_path_dir/part2/client_$i.txt"; then
            scores[cross_verification_student_server_ta_client_part2]=$((scores[cross_verification_student_server_ta_client_part2] + 1))
        fi
    done
}


cross_verification_student_server_ta_client_part3_aloha(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$test_case" ../temp/part3/testcase.txt
    cp "$config_file_part3" ../temp/part3/config.json
    temp_file=$(mktemp)
    { time make -C ../temp/part3 server-aloha >> log.txt 2>&1; } 2> "$temp_file"
    make -C "$ta_submission_path_dir/part3" client-aloha >> log.txt 2>&1
    execution_times[cross_verification_student_server_ta_client_part3_aloha_time]=$(grep '^user' "$temp_file" | awk '{print $2}')
    rm "$temp_file"
    rm ../temp/part3/testcase.txt
    for i in $(seq 1 $num_clients); do
        if diff -q "$output" "$ta_submission_path_dir/part3/client_$i.txt"; then
            scores[cross_verification_student_server_ta_client_part3_aloha]=$((scores[cross_verification_student_server_ta_client_part3_aloha] + 1))
        fi
    done
}

cross_verification_student_server_ta_client_part3_beb(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$test_case" ../temp/part3/testcase.txt
    cp "$config_file_part3" ../temp/part3/config.json
    temp_file=$(mktemp)
    { time make -C ../temp/part3 server-beb >> log.txt 2>&1; } 2> "$temp_file"
    make -C "$ta_submission_path_dir/part3" client-beb >> log.txt 2>&1
    execution_times[cross_verification_student_server_ta_client_part3_beb_time]=$(grep '^user' "$temp_file" | awk '{print $2}')
    rm "$temp_file" 
    rm ../temp/part3/testcase.txt
    for i in $(seq 1 $num_clients); do
        if diff -q "$output" "$ta_submission_path_dir/part3/client_$i.txt"; then
            scores[cross_verification_student_server_ta_client_part3_beb]=$((scores[cross_verification_student_server_ta_client_part3_beb] + 1))
        fi
    done
}

cross_verification_student_server_ta_client_part3_cscd(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$test_case" ../temp/part3/testcase.txt
    cp "$config_file_part3" ../temp/part3/config.json
    temp_file=$(mktemp)
    { time make -C ../temp/part3 server-cscd >> log.txt 2>&1; } 2> "$temp_file"
    make -C "$ta_submission_path_dir/part3" client-cscd >> log.txt 2>&1
    execution_times[cross_verification_student_server_ta_client_part3_cscd_time]=$(grep '^user' "$temp_file" | awk '{print $2}')
    rm "$temp_file"
    rm ../temp/part3/testcase.txt
    for i in $(seq 1 $num_clients); do
        if diff -q "$output" "$ta_submission_path_dir/part3/client_$i.txt"; then
            scores[cross_verification_student_server_ta_client_part3_cscd]=$((scores[cross_verification_student_server_ta_client_part3_cscd] + 1))
        fi
    done
}

cross_verification_student_server_ta_client_part4_fifo(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$test_case" ../temp/part4/testcase.txt
    cp "$config_file_part4" ../temp/part4/config.json
    temp_file=$(mktemp)
    { time make -C ../temp/part4 server-fifo >> log.txt 2>&1; } 2> "$temp_file"
    make -C "$ta_submission_path_dir/part4" client-fifo >> log.txt 2>&1
    execution_times[cross_verification_student_server_ta_client_part4_fifo_time]=$(grep '^user' "$temp_file" | awk '{print $2}')
    rm "$temp_file"
    rm ../temp/part4/testcase.txt
    for i in $(seq 1 $num_clients); do
        if diff -q "$output" "$ta_submission_path_dir/part4/client_$i.txt"; then
            scores[cross_verification_student_server_ta_client_part4_fifo]=$((scores[cross_verification_student_server_ta_client_part4_fifo] + 1))
        fi
    done
}

cross_verification_student_server_ta_client_part4_rr(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$test_case" ../temp/part4/testcase.txt
    cp "$config_file_part4" ../temp/part4/config.json
    temp_file=$(mktemp)
    { time make -C ../temp/part4 server-rr >> log.txt 2>&1; } 2> "$temp_file"
    make -C "$ta_submission_path_dir/part4" client-rr >> log.txt 2>&1
    execution_times[cross_verification_student_server_ta_client_part4_rr_time]=$(grep '^user' "$temp_file" | awk '{print $2}')
    rm "$temp_file"
    rm ../temp/part4/testcase.txt
    co=0
    for i in $(seq 1 $num_clients); do
        if diff -q "$output" "$ta_submission_path_dir/part4/client_$i.txt"; then
            co=$((co + 1))
            scores[cross_verification_student_server_ta_client_part4_rr]=$((scores[cross_verification_student_server_ta_client_part4_rr] + 1))
        fi
    done
    scores[cross_verification_student_server_ta_client_part4_rr]=$((co))
}

cross_verification_ta_server_student_client_part1(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$config_file_part1" ../temp/part1/config.json
    temp_file=$(mktemp)
    { time make -C ../temp/part1 client >> log.txt 2>&1; } 2> "$temp_file"
    make -C "$ta_submission_path_dir/part1" server >> log.txt 2>&1
    execution_times[cross_verification_ta_server_student_client_part1_time]=$(grep '^user' "$temp_file" | awk '{print $2}')
    rm "$temp_file" 
    for i in $(seq 1 1); do
        if diff -q "$output" "$../temp/part1/client_$i.txt"; then
            scores[cross_verification_ta_server_student_client_part1]=$((scores[cross_verification_ta_server_student_client_part1] + 1))
        fi
    done
    rm ../temp/part1/client_*.txt
}

cross_verification_ta_server_student_client_part2(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$config_file_part2" ../temp/part2/config.json
    temp_file=$(mktemp)
    { time make -C ../temp/part2 client >> log.txt 2>&1; } 2> "$temp_file"
    make -C "$ta_submission_path_dir/part2" server  >> log.txt 2>&1
    execution_times[cross_verification_ta_server_student_client_part2_time]=$(grep '^user' "$temp_file" | awk '{print $2}')
    rm "$temp_file"
    for i in $(seq 1 $num_clients); do
        if diff -q "$output" "$../temp/part2/client_$i.txt"; then
            scores[cross_verification_ta_server_student_client_part2]=$((scores[cross_verification_ta_server_student_client_part2] + 1))
        fi
    done
    rm ../temp/part2/client_*.txt
}

cross_verification_ta_server_student_client_part3_aloha(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$config_file_part3" ../temp/part3/config.json
    temp_file=$(mktemp)
    { time make -C ../temp/part3 client-aloha >> log.txt 2>&1; } 2> "$temp_file"
    make -C "$ta_submission_path_dir/part3" server-aloha  >> log.txt 2>&1
    execution_times[cross_verification_ta_server_student_client_part3_aloha_time]=$(grep '^user' "$temp_file" | awk '{print $2}')
    rm "$temp_file"
    for i in $(seq 1 $num_clients); do
        if diff -q "$output" "$../temp/part3/client_$i.txt"; then
            scores[cross_verification_ta_server_student_client_part3_aloha]=$((scores[cross_verification_ta_server_client_part3_aloha] + 1))
        fi
    done
    rm ../temp/part3/client_*.txt
}

cross_verification_ta_server_student_client_part3_beb(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$config_file_part3" ../temp/part3/config.json
    temp_file=$(mktemp)
    { time make -C ../temp/part3 client-beb >> log.txt 2>&1; } 2> "$temp_file"
    make -C "$ta_submission_path_dir/part3" server-beb >> log.txt 2>&1
    execution_times[cross_verification_ta_server_student_client_part3_beb_time]=$(grep '^user' "$temp_file" | awk '{print $2}')
    rm "$temp_file"
    for i in $(seq 1 $num_clients); do
        if diff -q "$output" "$../temp/part3/client_$i.txt"; then
            scores[cross_verification_ta_server_student_client_part3_beb]=$((scores[cross_verification_ta_server_client_part3_beb] + 1))
        fi
    done
    rm ../temp/part3/client_*.txt
}

cross_verification_ta_server_student_client_part3_cscd(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$config_file_part3" ../temp/part3/config.json
    temp_file=$(mktemp)
    { time make -C ../temp/part3 client-cscd >> log.txt 2>&1; } 2> "$temp_file"
    make -C "$ta_submission_path_dir/part3" server-cscd >> log.txt 2>&1
    execution_times[cross_verification_ta_server_student_client_part3_cscd_time]=$(grep '^user' "$temp_file" | awk '{print $2}')
    rm "$temp_file"
    for i in $(seq 1 $num_clients); do
        if diff -q "$output" "$../temp/part3/client_$i.txt"; then
            scores[cross_verification_ta_server_student_client_part3_cscd]=$((scores[cross_verification_ta_server_client_part3_cscd] + 1))
        fi
    done
    rm ../temp/part3/client_*.txt
}

cross_verification_ta_server_student_client_part4_fifo(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$config_file_part4" ../temp/part4/config.json
    temp_file=$(mktemp)
    { time make -C ../temp/part4 client-fifo >> log.txt 2>&1; } 2> "$temp_file"
    make -C "$ta_submission_path_dir/part4" server-fifo >> log.txt 2>&1
    execution_times[cross_verification_ta_server_student_client_part4_fifo_time]=$(grep '^user' "$temp_file" | awk '{print $2}')
    rm "$temp_file"
    for i in $(seq 1 $num_clients); do
        if diff -q "$output" "$../temp/part4/client_$i.txt"; then
            scores[cross_verification_ta_server_student_client_part4_fifo]=$((scores[cross_verification_ta_server_client_part4_fifo] + 1))
        fi
    done
    rm ../temp/part4/client_*.txt
}

cross_verification_ta_server_student_client_part4_rr(){
    local entry_num1=$1
    local entry_num2=$2
    cp "$test_case" ../temp/part4/testcase.txt
    cp "$config_file_part4" ../temp/part4/config.json
    temp_file=$(mktemp)
    { time make -C ../temp/part4 client-rr >> log.txt 2>&1; } 2> "$temp_file"
    make -C "$ta_submission_path_dir/part4" server-rr >> log.txt 2>&1
    execution_times[cross_verification_ta_server_student_client_part4_rr_time]=$(grep '^user' "$temp_file" | awk '{print $2}')
    rm "$temp_file"
    rm ../temp/part4/testcase.txt
    for i in $(seq 1 $num_clients); do
        if diff -q "$output" "$../temp/part4/client_$i.txt"; then
            scores[cross_verification_ta_server_student_client_part4_rr]=$((scores[cross_verification_ta_server_student_client_part4_rr] + 1))
        fi
    done
    rm ../temp/part4/client_*.txt
}
# a -> student client verification
# b -> ta client verification
# s -> score
# t -> execution time
echo "Entry Number, s1, s2, s3.1, s3.2, s3.3, s4.1, s4.2, sa1, sa2, sa3.1, sa3.2, sa3.3, sa4.1, sa4.2, sb1, sb2, sb3.1, sb3.2, sb3.3, sb4.1, sb4.2, t1, t2, t3, t4, ta1, ta2, ta3.1, ta3.2, ta3.3, ta4.1, ta4.2, tb1, tb2, tb3.1, tb3.2, tb3.3, tb4.1, tb4.2" > "$scores_path"
# loop over submissions
for student_submission_path in $student_submission_path_dir/*; do
    # Student submission path
    if  [[ "$(basename "$student_submission_path")" =~ $pattern ]] &&  file "$student_submission_path" | grep -q 'Zip archive data'; then
        echo "Valid submission"
        entry_num1=$(echo "$(basename "$student_submission_path")" | cut -d '_' -f 1)
        entry_num2=$(echo "$(basename "$student_submission_path")" | cut -d '_' -f 2 | cut -d '.' -f 1)
        echo "Entry Number 1: $entry_num1"
        echo "Entry Number 2: $entry_num2"
        unzip -o -q "$student_submission_path" -d ../temp/
        part1_plot_execution_time_extraction $entry_num1 $entry_num2
        part2_plot_execution_time_extraction $entry_num1 $entry_num2
        part3_plot_execution_time_extraction $entry_num1 $entry_num2
        part4_plot_execute_time_fairness_extraction $entry_num1 $entry_num2
        cross_verification_ta_server_student_client_part1 $entry_num1 $entry_num2
        cross_verification_ta_server_student_client_part2 $entry_num1 $entry_num2
        cross_verification_ta_server_student_client_part3_aloha $entry_num1 $entry_num2
        cross_verification_ta_server_student_client_part3_beb $entry_num1 $entry_num2
        cross_verification_ta_server_student_client_part3_cscd $entry_num1 $entry_num2
        cross_verification_ta_server_student_client_part4_fifo $entry_num1 $entry_num2
        cross_verification_ta_server_student_client_part4_rr $entry_num1 $entry_num2
        cross_verification_student_server_ta_client_part1 $entry_num1 $entry_num2
        cross_verification_student_server_ta_client_part2 $entry_num1 $entry_num2
        cross_verification_student_server_ta_client_part3_aloha $entry_num1 $entry_num2
        cross_verification_student_server_ta_client_part3_beb $entry_num1 $entry_num2
        cross_verification_student_server_ta_client_part3_cscd $entry_num1 $entry_num2
        cross_verification_student_server_ta_client_part4_fifo $entry_num1 $entry_num2
        cross_verification_student_server_ta_client_part4_rr $entry_num1 $entry_num2
        echo "$entry_num1,$entry_num2,${scores[part1]},${scores[part2]},${scores[part3_aloha]},${scores[part3_beb]},${scores[part3_cscd]},${scores[part4_fifo]},${scores[part4_rr]},${scores[cross_verification_ta_server_student_client_part1]},${scores[cross_verification_ta_server_student_client_part2]},${scores[cross_verification_ta_server_student_client_part3_aloha]},${scores[cross_verification_ta_server_student_client_part3_beb]},${scores[cross_verification_ta_server_student_client_part3_cscd]},${scores[cross_verification_ta_server_student_client_part4_fifo]},${scores[cross_verification_ta_server_student_client_part4_rr]},${scores[cross_verification_student_server_ta_client_part1]},${scores[cross_verification_student_server_ta_client_part2]},${scores[cross_verification_student_server_ta_client_part3_aloha]},${scores[cross_verification_student_server_ta_client_part3_beb]},${scores[cross_verification_student_server_ta_client_part3_cscd]},${scores[cross_verification_student_server_ta_client_part4_fifo]},${scores[cross_verification_student_server_ta_client_part4_rr]},${execution_times[part1_time]},${execution_times[part2_time]},${execution_times[part3_time]},${execution_times[part4_time]},${execution_times[cross_verification_ta_server_student_client_part1_time]},${execution_times[cross_verification_ta_server_student_client_part2_time]},${execution_times[cross_verification_ta_server_student_client_part3_aloha_time]},${execution_times[cross_verification_ta_server_student_client_part3_beb_time]},${execution_times[cross_verification_ta_server_student_client_part3_cscd_time]},${execution_times[cross_verification_ta_server_student_client_part4_fifo_time]},${execution_times[cross_verification_ta_server_student_client_part4_rr_time]},${execution_times[cross_verification_student_server_ta_client_part1_time]},${execution_times[cross_verification_student_server_ta_client_part2_time]},${execution_times[cross_verification_student_server_ta_client_part3_aloha_time]},${execution_times[cross_verification_student_server_ta_client_part3_beb_time]},${execution_times[cross_verification_student_server_ta_client_part3_cscd_time]},${execution_times[cross_verification_student_server_ta_client_part4_fifo_time]},${execution_times[cross_verification_student_server_ta_client_part4_rr_time]}" >> "$scores_path"
        rm -rf ../temp/*
    fi
done




