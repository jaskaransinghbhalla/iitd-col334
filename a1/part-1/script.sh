#!/bin/bash

# List of IP addresses
ip_addresses=(
    "192.168.1.58"
    "192.168.59.1"
    "192.168.27.69"
    "192.168.27.57"
    "192.168.27.109"
    "192.168.27.111"
    "192.168.27.107"
    "122.185.39.5"
    "182.79.247.94"
    "38.142.132.58"
    "190.92.147.9"
    "190.92.158.4"
)

# Output file
output_file="whois_results.txt"

# Clear the output file
> $output_file

# Loop through each IP address and run whois
for ip in "${ip_addresses[@]}"; do
    echo "Running whois for IP: $ip" >> $output_file
    whois $ip | grep -E "OrgName|Country|NetRange|CIDR|OriginAS" >> $output_file
    echo "--------------------------------------------" >> $output_file
done

echo "Whois lookup completed. Results saved to $output_file"