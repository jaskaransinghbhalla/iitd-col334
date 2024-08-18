# System packages
import argparse
from collections import defaultdict
import csv

# External libraries
from scapy.all import IP, TCP, Ether, sniff, rdpcap  # type: ignore
from datetime import datetime
import matplotlib.pyplot as plt  # type: ignore


# Define your packet filter using Scapy
def isolate_traffic(pkt):

    if Ether in pkt and IP in pkt and TCP in pkt:
        ether_layer = pkt[Ether]
        ip_layer = pkt[IP]
        tcp_layer = pkt[TCP]
        eth_condition = (
            ether_layer.src == "b8:81:98:9e:ba:01"
            and ether_layer.dst == "a8:da:0c:c5:b5:c3"
        ) or (
            ether_layer.dst == "b8:81:98:9e:ba:01"
            and ether_layer.src == "a8:da:0c:c5:b5:c3"
        )
        ip_condition = (
            ip_layer.src == "61.246.223.11" and ip_layer.dst == "192.168.29.159"
        ) or (ip_layer.dst == "61.246.223.11" and ip_layer.src == "192.168.29.159")

        # Doubtful about the ports to be used
        tcp_condition = (tcp_layer.dport == 46000 and tcp_layer.sport == 443) or (
            tcp_layer.sport == 46000 and tcp_layer.dport == 443
        )
        return eth_condition and ip_condition and tcp_condition
    else:
        return False


def is_download(src_ip, dst_ip):
    return src_ip == "61.246.223.11" and dst_ip == "192.168.29.159"


def is_upload(src_ip, dst_ip):
    return src_ip == "192.168.29.159" and dst_ip == "61.246.223.11"


def plot_time_series(filtered_packets):
    print("Plotting time series")
    download_speeds = defaultdict(list)
    upload_speeds = defaultdict(list)
    times = []

    start_time = filtered_packets[0].time
    end_time = filtered_packets[-1].time

    for packet in filtered_packets:
        timestamp = packet.time
        second = int(timestamp - start_time)
        src_ip = packet[IP].src
        dst_ip = packet[IP].dst
        buf = bytes(packet)
        data_len = len(buf) * 8 / 1e3

        if is_download(src_ip, dst_ip):
            download_speeds[second].append(data_len)
        elif is_upload(src_ip, dst_ip):
            upload_speeds[second].append(data_len)

    # Calculate average throughput per second
    avg_download_speeds = []
    avg_upload_speeds = []
    times = []

    for second in range(int(end_time - start_time) + 1):
        times.append(datetime.fromtimestamp(int(start_time + second)))
        avg_download_speeds.append(
            sum(download_speeds[second]) / max(1, len(download_speeds[second]))
        )
        avg_upload_speeds.append(
            sum(upload_speeds[second]) / max(1, len(upload_speeds[second]))
        )

    print("Generating a plot")
    # Download Speed Plot
    plt.figure(figsize=(10, 5))
    plt.fill_between(
        times,
        avg_download_speeds,
        alpha=0.5,
        label="Download Speed (Kbps)",
        color="#00BFFF",
    )
    plt.gca().spines["top"].set_visible(False)
    plt.gca().spines["right"].set_visible(False)
    plt.xticks(rotation=90)
    plt.ylabel("Speed (Kbps)")
    plt.xlabel("Time (in milliseconds)")
    plt.title("Download Speed Time Series")
    plt.legend()
    plt.tight_layout()
    plt.grid(True, which="both", ls="-", alpha=0.2)
    plt.savefig("./time_series_download.png", dpi=1200, bbox_inches="tight")
    plt.close()

    # Upload Speed Plot
    plt.figure(figsize=(10, 5))
    plt.fill_between(
        times,
        avg_upload_speeds,
        alpha=0.5,
        label="Upload Speed (Kbps)",
        color="red",
    )
    plt.gca().spines["top"].set_visible(False)
    plt.gca().spines["right"].set_visible(False)
    plt.xticks(rotation=90)
    plt.ylabel("Speed (Kbps)")
    plt.xlabel("Time (in milliseconds)")
    plt.title("Upload Speed Time Series")
    plt.legend()
    plt.tight_layout()
    plt.grid(True, which="both", ls="-", alpha=0.2)
    plt.savefig("./time_series_upload.png", dpi=1200, bbox_inches="tight")
    plt.close("all")

    print("Plots saved as download_speed_chart.png and upload_speed_chart.png")


def calculate_speed(filtered_packets):
    print("Calculating download and upload speed")

    if not filtered_packets:
        return 0, 0

    start_time = filtered_packets[0].time
    end_time = filtered_packets[-1].time
    duration = (int)(end_time - start_time)
    print(duration)
    download = 0
    upload = 0

    for packet in filtered_packets:
        src_ip = packet[IP].src
        dst_ip = packet[IP].dst
        buf = bytes(packet)
        data_len = len(buf) * 8 / 1e6  # Convert to Mbps

        if is_download(src_ip, dst_ip):
            download += data_len
        elif is_upload(src_ip, dst_ip):
            upload += data_len
    if duration > 0:
        avg_download_speed = download / duration
        avg_upload_speed = upload / duration
    else:
        avg_download_speed = 0
        avg_upload_speed = 0

    avg_download_speed = round(avg_download_speed, 3)
    avg_upload_speed = round(avg_upload_speed, 3)

    save_as_csv(
        avg_download_speed=avg_download_speed,
        avg_upload_speed=avg_upload_speed,
    )
    print(f"{avg_download_speed} Mbps", f"{avg_upload_speed} Mbps")
    return avg_download_speed, avg_upload_speed


# Calculate speeds


def save_as_csv(avg_download_speed, avg_upload_speed, filename="network_speeds.csv"):
    with open(filename, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["Download Speed (Mbps)", "Upload Speed (Mbps)"])
        csvwriter.writerow([avg_download_speed, avg_upload_speed])
    print(f"Data saved to {filename}")


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("pcap_file")
    parser.add_argument("--plot", action="store_true")
    parser.add_argument(
        "--throughput",
        action="store_true",
    )
    args = parser.parse_args()

    print("Isolating network traffic")
    packets = rdpcap(args.pcap_file)
    filtered_packets = sniff(offline=args.pcap_file, lfilter=isolate_traffic)
    total_packets = len(packets)
    total_filtered_packets = len(filtered_packets)
    print(
        f"Percentage of packets in Speed Test: {total_filtered_packets/total_packets*100:.2f}%"
    )
    if args.plot:
        plot_time_series(filtered_packets)

    if args.throughput:
        calculate_speed(filtered_packets)


if __name__ == "__main__":

    main()
