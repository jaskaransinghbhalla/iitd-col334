// Client

// Packages
#include "json.hpp"
#include <algorithm>
#include <arpa/inet.h>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <netdb.h>
#include <sstream>
#include <string>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

// Global variables
int num_clients = 1;
int num_word_per_request;
int offset = 0;
int port;
int words_per_packet;
std::string ip_address;
std::string output_file = "output.txt";
std::map<std::string, int> wordFrequency;

// Constants
const int BUFFER_SIZE = 1024;

void read_config()
{
    try
    {
        // Open the config file
        std::ifstream file("config.json");
        nlohmann::json config;
        file >> config;

        // Access data from the JSON
        ip_address = config["server_ip"];
        num_clients = config["num_clients"];
        num_word_per_request = config["k"];
        port = config["server_port"];
        words_per_packet = config["p"];
    }
    catch (nlohmann::json::exception &e)
    {
        std::cerr << "JSON parsing error: " << e.what() << std::endl;
    }
}

int connect_to_server()
{
    // Client-side socket
    int client_sock_fd = socket(AF_INET, SOCK_STREAM, 0);

    // Check for successfull creation of client socket
    if (client_sock_fd == -1)
    {
        perror("Socker creation failed");
        exit(EXIT_FAILURE);
    }

    // Address definitions for client-side socket
    sockaddr_in address;
    int address_len = sizeof(address);
    if (ip_address == "0.0.0.0" || ip_address == "INADDR_ANY")
    {
        // If the config specifies 0.0.0.0 or INADDR_ANY, use INADDR_ANY // connecting to server on any IP address
        address.sin_addr.s_addr = INADDR_ANY;
    }
    else
    {
        // Otherwise, use the IP address from the config file
        if (inet_pton(AF_INET, ip_address.c_str(), &address.sin_addr) <= 0)
        {
            std::cerr << "Invalid address/ Address not supported" << std::endl;
        }
    }

    address.sin_family = AF_INET;
    address.sin_port = htons(port);

    // Establishing a connections to server and check for connections failure
    if (connect(client_sock_fd, (struct sockaddr *)&address, address_len) < 0)
    {
        perror("Connection failed");
        exit(EXIT_FAILURE);
    }

    // Connected to server successfully
    std::cout << "Connected to server : " << ip_address << ":" << port << std::endl;
    return client_sock_fd;
}

void count_word(const std::string &word)
{
    std::string s = "";
    s += EOF;
    if (word != "\n" && word != s) // check this exactly
    {
        wordFrequency[word]++;
    }
}

std::string process_packet(const std::string &packet_data)
{
    std::vector<std::string> words;
    std::istringstream iss(packet_data);
    std::string word;

    while (std::getline(iss, word, ','))
    {
        // Remove leading/trailing whitespace
        word.erase(0, word.find_first_not_of(" \t\n\r\f\v"));
        word.erase(word.find_last_not_of(" \t\n\r\f\v") + 1);

        if (!word.empty())
        {
            words.push_back(word);
        }
    }

    for (const auto &w : words)
    {
        count_word(w);
    }

    return words.empty() ? "" : words.back();
}

void request_words(int client_sock_fd)
{
    // Buffer array to read
    char buffer[BUFFER_SIZE] = {0};
    std::string lastWord;
    bool eof = false;
    // Send the requests until u recieve an EOF
    while (true)
    {
        // Clear the buffer
        // memset(buffer, 0, BUFFER_SIZE);

        // Converting offset to the required api level syntax
        std::string req_payload = std::to_string(offset) + "\n";

        // Sending the request

        // client_sock_fd: This is the first argument to send(). It's a file descriptor representing the client socket to which the data will be sent.
        // request.c_str(): This is the second argument. It's the buffer containing the data to be sent. Here, request appears to be a string object (likely std::string), and c_str() returns a pointer to a null-terminated character array (C-style string) containing the string's data.
        // request.length(): This is the third argument, specifying the number of bytes to send from the buffer. It's using the length() method of the string object to get the exact length of the string.
        // 0: This is the fourth argument, which represents flags. In this case, no special flags are being used (0 means default behavior).
        if (send(client_sock_fd, req_payload.c_str(), req_payload.length(), 0) < -1)
        {
            perror("Client request failed");
            exit(EXIT_FAILURE);
        }
        // std ::cout << "Request sent : " << req_payload << std::endl;

        // Invalid Offset
        if (strcmp(buffer, "$$\n") == 0)
        {
            break;
        }

        // Valid Offset

        // Reading a packet
        int word_count = 0;
        std::string last_word;
        std::string accumulated_data;
        while (word_count < num_word_per_request)
        {
            char buffer_temp[2] = {0}; // 2 bytes
            memset(buffer_temp, 0, 2);

            int valread = recv(client_sock_fd, buffer_temp, 1, 0);

            if (valread < 0)
            {
                perror("Error reading from server");
                exit(EXIT_FAILURE);
            }

            if (*buffer_temp == '\n')
            {
                // std::cout << "Packet received" << std::endl;
                // std ::cout << "Received : " << accumulated_data << std::endl;
                last_word = process_packet(accumulated_data);
                // std ::cout << "Last word is " << last_word << std::endl;

                // Check for EOF
                std::string s = "";
                s += EOF;
                if (last_word == s)
                {
                    eof = true;
                    break;
                }

                word_count += words_per_packet;
                accumulated_data = "";
            }
            else
            {
                accumulated_data += buffer_temp[0];
            }

        }
        if (!eof)
        {
            offset += num_word_per_request;
        }
        else
        {
            break;
        }
    }

    // Close the socket connection
    close(client_sock_fd);
}

void write_with_of_stream(const std::string &filename, const std::string &content, bool append = false)
{
    std::ofstream outFile;

    if (append)
    {
        outFile.open(filename, std::ios_base::app);
    }
    else
    {
        outFile.open(filename);
    }

    if (outFile.is_open())
    {
        outFile << content;
        outFile.close();
    }
}

void print_word_freq()
{
    write_with_of_stream(output_file, "", false);
    std::vector<std::pair<std::string, int>> pairs;
    for (const auto &item : wordFrequency)
    {
        pairs.push_back(item);
    }
    std::sort(pairs.begin(), pairs.end());

    for (const auto &pair : pairs)
    {
        std::string result = pair.first + ",";
        result += std::to_string(pair.second) + '\n';
        write_with_of_stream(output_file, result, true);
    }
}

void client()
{
    // Create a client socket and connect that to the server address
    int client_sock_fd = connect_to_server();

    // Send a request for words to a client
    request_words(client_sock_fd);

    // Print the fequency of words
    print_word_freq();

    std::cout << "Disconnect Server" << std::endl;
}

int main()
{
    // read config.json
    read_config();

    // create a client
    client();
}
