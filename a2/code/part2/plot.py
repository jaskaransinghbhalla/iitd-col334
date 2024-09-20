import numpy as np
import json
import subprocess
import matplotlib.pyplot as plt
import time
from scipy import stats
import os
import signal

def generate_config(num_clients):
    return {
        "input_file": "words.txt",
        "k": 10,
        "num_clients": num_clients,
        "p": 10,
        "server_ip": "127.0.0.1",
        "server_port": 3000,
    }

def run_process(command):
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        return process
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running '{' '.join(command)}': {e}")
        return None
    except FileNotFoundError:
        print(f"Error: '{command[0]}' command not found. Please ensure it's installed and in your PATH.")
        return None

def main():
    run_process(["make", "server"])
    run_process(["make", "client"])
    
    avg_times = []
    confidence_intervals = []
    num_clients_list = [1, 4, 8, 12, 16, 20,24,28, 32]
    
    for num_clients in num_clients_list:
        print(f"Running with {num_clients} clients")
        config = generate_config(num_clients)
        filename = "config.json"
        with open(filename, "w") as f:
            json.dump(config, f, indent=2)
        
        with open("durations.txt", "w") as f:
            f.write("")
        
        # Start the server
        server_process = run_process(["./server"])
        if not server_process:
            print("Failed to start server")
            continue
        
        # Give the server some time to start up
        time.sleep(2)
        
        # Run the client
        client_process = run_process(["./client"])
        if not client_process:
            print("Failed to start client")
            server_process.terminate()
            continue
        
        # Wait for the client to finish
        client_process.wait()

        time.sleep(2)
        
        # Terminate the server
        server_process.terminate()
        
        # Read the results
        with open("durations.txt", "r") as f:
            times = [float(line.strip(',')) for line in f.read().split(',') if line.strip()]
        
        avg_time = np.mean(times)
        avg_time_seconds = avg_time / 1000  
        avg_times.append(avg_time_seconds)
        
    time.sleep(5)
    print(f"Average times: {avg_times}")
    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.plot(num_clients_list, avg_times, "o-")
    plt.xticks(num_clients_list)
    plt.title("Average Completion Time vs Number of Clients with 95% Confidence Intervals")
    plt.xlabel("Number of Clients")
    plt.ylabel("Average Time (s)")
    plt.grid(True)
    plt.savefig("./plot.png")
    plt.close()
    make_process = run_process(["make", "clean"])

if __name__ == "__main__":
    main()