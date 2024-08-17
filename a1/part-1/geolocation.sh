#!/bin/bash
# Output file
output_file="geo-dns-sigcomm-cellular.txt"

# List of IP addresses
# IIT Delhi - google

# ip_addresses=(
#     "10.194.0.13"
#     "10.254.239.5"
#     "10.254.239.1"
#     "10.255.107.3"
#     "10.119.233.65"
#     "10.119.234.162"
#     "72.14.195.56"
#     "142.251.226.85"
#     "192.178.83.243"
#     "142.251.76.169"
#     "142.251.76.171"
#     "142.250.207.206"
# )

# Cellular - Google

# ip_addresses=(
#     "192.168.1.58"
#     "192.168.59.1"
#     "192.168.27.57"
#     "192.168.27.107"
#     "192.168.27.105"
#     "122.185.39.5"
#     "122.185.39.1"
#     "142.251.49.114"
#     "142.250.193.206"
#     "142.251.54.97"
# )

# IIT Delhi - sigcomm

# ip_addresses=(
#     "10.194.0.13"
#     "10.254.239.5"
#     "10.254.239.1"
#     "10.255.107.3"
#     "10.119.233.65"
#     "10.119.234.162"
#     "136.232.148.177"
#     "49.45.4.103"
#     "4.7.26.61"
#     "4.69.203.81"
#     "4.69.202.222"
#     "4.31.124.142"
#     "69.48.136.9"
#     "190.92.158.4"
# )

# Cellular - sigcomm

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




# Clear the output file
> $output_file

# Loop through each IP address and run whois
for ip in "${ip_addresses[@]}"; do
    # echo "Running nslookup for IP: $ip" >> $output_file
    # nslookup $ip >> $output_file
    # echo "Running dig for IP: $ip" >> $output_file
    # dig -x $ip >> $output_file
    echo "Running host for IP: $ip" >> $output_file
    curl ipinfo.io/$ip >> $output_file
    # whois $ip | grep -E "OrgName|Country|NetRange|CIDR|OriginAS" >> $output_file
    echo "--------------------------------------------" >> $output_file
done

echo "Whois lookup completed. Results saved to $output_file"