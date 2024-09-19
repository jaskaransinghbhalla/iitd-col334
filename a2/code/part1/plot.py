import numpy as np
import json
import subprocess
import matplotlib.pyplot as plt
import time
from scipy import stats


def generate_config(p):
    return {
        "input_file": "words.txt",
        "k": 10,
        "num_clients": 1,
        "p": p,
        "server_ip": "127.0.0.1",
        "server_port": 3000,
    }


def run_make_process():
    try:
        start_time = time.time()
        process = subprocess.Popen(
            ["make", "run"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        return_code = process.wait()
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000
        return return_code, execution_time
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running 'make run': {e}")
        return e.returncode, None
    except FileNotFoundError:
        print(
            "Error: 'make' command not found. Please ensure it's installed and in your PATH."
        )
        return 1, None


def main():
    avg_times = []
    confidence_intervals = []

    for p in range(1, 11):
        config = generate_config(p)
        filename = f"config.json"
        with open(filename, "w") as f:
            json.dump(config, f, indent=2)

        times = []
        for i in range(10):  # Run 10 times for each p value
            return_code, execution_time = run_make_process()
            if execution_time is not None:
                times.append(execution_time)

        avg_time = np.mean(times)
        avg_times.append(avg_time)

        # Calculate 95% confidence interval
        ci = stats.t.interval(
            confidence=0.95, df=len(times) - 1, loc=avg_time, scale=stats.sem(times)
        )
        confidence_intervals.append(
            (ci[1] - ci[0]) / 2
        )  # Store the half-width of the CI

        # print(
        #     f"p={p}: Avg time = {avg_time:.2f} ms, CI = ±{(ci[1] - ci[0]) / 2:.2f} ms"
        # )

    # Create the plot
    x = np.arange(1, 11)
    plt.figure(figsize=(10, 6))
    plt.errorbar(
        x, avg_times, yerr=confidence_intervals, fmt="o-", capsize=5, capthick=2
    )
    plt.title("Average Completion Time vs p with 95% Confidence Intervals")
    plt.xlabel("p")
    plt.ylabel("Average Time (ms)")
    plt.grid(True)
    plt.savefig("./plot.png")
    plt.close()


if __name__ == "__main__":
    main()
