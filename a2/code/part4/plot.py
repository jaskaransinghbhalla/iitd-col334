from tracemalloc import start
import numpy as np
import json
import subprocess
import matplotlib.pyplot as plt
import time
from scipy import stats
import os
import signal

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


def generate_config(num_clients):
    return {
        "input_file": "words.txt",
        "k": 10,
        "num_clients": num_clients,
        "p": 10,
        "server_ip": "127.0.0.1",
        "server_port": 3000,
    }

def compare_policies():
    run_process(["make", "server"])
    run_process(["make", "client"])
    num_clients_list = [1, 2, 4, 8, 16]
    fifo_times = []
    rr_times = []
    for num_clients in num_clients_list:
            
            print(f"Running with {num_clients} clients")

            # Generate the config file
            config = generate_config(num_clients)
            filename = "config.json"
            with open(filename, "w") as f:
                json.dump(config, f, indent=2)
            
            # Fifo
            print("Running FIFO")
            # Start the server
            start = time.time()
            server_process = run_process(["make", "run-fifo"])
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
            end = time.time()

            fifo_times.append(end - start)

            # Round Robin
            print("Running Round Robin")
            # Start the server
            start = time.time()
            server_process = run_process(["make", "run-rr"])
            if not server_process:
                print("Failed to start server")
                continue

            time.sleep(2)

            client_process = run_process(["./client"])
            if not client_process:
                print("Failed to start client")
                server_process.terminate()
                continue

            client_process.wait()

            time.sleep(2)

            server_process.terminate()

            end = time.time()

            rr_times.append(end - start)
            
    print(f"Fifo times: {fifo_times}")
    print(f"RR times: {rr_times}")
    plt.figure(figsize=(10, 6))
    plt.plot(num_clients_list, fifo_times, label="FIFO")
    plt.plot(num_clients_list, rr_times, label="Round Robin")
    plt.xlabel("Number of Clients (num_clients)")
    plt.ylabel("Average completion time")
    plt.title("FIFO vs Round Robin Scheduling")
    plt.legend()
    plt.grid(True)
    plt.savefig("plot.png")
    run_process(["make", "cleanall"])    
    


def main():
    compare_policies()


if __name__ == "__main__":
    main()
