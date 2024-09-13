// Client

// Packages
#include "json.hpp"     // JSON Library
#include <algorithm>    // Provides a collection of functions especially designed to be used on ranges of elements
#include <arpa/inet.h>  // Provides functions for manipulating IP addresses (like inet_addr)
#include <cstring>      // Provides functions for manipulating C strings and arrays
#include <fstream>      // Provides file stream classes for reading/writing files
#include <iostream>     // Provides input/output stream objects like cin, cout, cerr
#include <map>          // Provides a collection of key-value pairs
#include <netdb.h>      // Provides functions for network address and service translation
#include <sstream>      // Provides classes for string streams
#include <string>       // Provides string class
#include <sys/socket.h> // Includes core functions and structures for socket programming
#include <sys/types.h>  // Provides data types used in system calls
#include <unistd.h>     // Provides POSIX operating system API like close()

// Global variables
int num_clients = 1;
int num_word_per_request;
int offset = 0;
int port;
int words_per_packet;
std::map<std::string, int> wordFrequency;
std::string ip_address;
std::string output_file = "output.txt";

// Constants
const int BUFFER_SIZE = 1024;

void read_config() // Read the config file
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

int connect_to_server() // Connect to the server
{
    int client_sock_fd = socket(AF_INET, SOCK_STREAM, 0); // Client-side socket
    if (client_sock_fd == -1)                             // Check for successfull creation of client socket
    {
        perror("Socker creation failed");
        exit(EXIT_FAILURE);
    }
    sockaddr_in address; // Address definitions for client-side socket
    int address_len = sizeof(address);
    if (ip_address == "0.0.0.0" || ip_address == "INADDR_ANY")
    {

        address.sin_addr.s_addr = INADDR_ANY; // If the config specifies 0.0.0.0 or INADDR_ANY, use INADDR_ANY // connecting to server on any IP address
    }
    else
    {
        if (inet_pton(AF_INET, ip_address.c_str(), &address.sin_addr) <= 0) // Otherwise, use the IP address from the config file
        {
            std::cerr << "Invalid address/ Address not supported" << std::endl;
        }
    }
    address.sin_family = AF_INET;                                              // Set the address family to AF_INET
    address.sin_port = htons(port);                                            // Convert port to network byte order
    if (connect(client_sock_fd, (struct sockaddr *)&address, address_len) < 0) // Establishing a connections to server and check for connections failure
    {
        perror("Connection failed");
        exit(EXIT_FAILURE);
    }
    std::cout << "Connected to server : " << ip_address << ":" << port << std::endl; // Connected to server successfully
    return client_sock_fd;
}

void count_word(const std::string &word) // Count the frequency of words
{
    std::string s = "";
    s += EOF;
    if (word != "\n" && word != s) // check this exactly
    {
        wordFrequency[word]++;
    }
}

std::string process_packet(const std::string &packet_data) // Process the packet data
{
    std::vector<std::string> words;
    std::istringstream iss(packet_data);
    std::string word;
    while (std::getline(iss, word, ','))
    {
        word.erase(0, word.find_first_not_of(" \t\n\r\f\v")); // Remove leading whitespace
        word.erase(word.find_last_not_of(" \t\n\r\f\v") + 1); // Remove trailing whitespace
        words.push_back(word);                                // Add the word to the vector
    }

    for (const auto &w : words)
    {
        count_word(w);
    }
    return words.empty() ? "" : words.back();
}

void request_words(int client_sock_fd) // Request words from the server
{
    // Buffer array to read
    char buffer[BUFFER_SIZE] = {0};
    std::string lastWord;
    bool eof = false;
    // Send the requests until u recieve an EOF
    while (true)
    {

        std::string req_payload = std::to_string(offset) + "\n";                     // Converting offset to the required api level syntax
        if (send(client_sock_fd, req_payload.c_str(), req_payload.length(), 0) < -1) // Sending the request
        {
            perror("Client request failed");
            exit(EXIT_FAILURE);
        }
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
            char buffer_temp[2] = {0};                             // 2 bytes
            memset(buffer_temp, 0, 2);                             // Clear the buffer
            int valread = recv(client_sock_fd, buffer_temp, 1, 0); // Read data from the client socket into the buffer
            if (valread < 0)                                       // If the read operation fails
            {
                perror("Error reading from server");
                exit(EXIT_FAILURE);
            }
            // If the buffer contains a newline character
            if (*buffer_temp == '\n')
            {
                last_word = process_packet(accumulated_data); // Process the accumulated data and get the last word
                std::string s = "";                           // Check for EOF
                s += EOF;
                if (last_word == s)
                {
                    eof = true;
                    break;
                }

                word_count += words_per_packet;
                accumulated_data = "";
            }
            // If the buffer does not contain a newline character
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

    close(client_sock_fd);                         // Close the socket connection
    std::cout << "Disconnect Server" << std::endl; // Disconnect the server
}

void write_with_of_stream(const std::string &filename, const std::string &content, bool append = false) // Write to a file
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

void print_word_freq() // Print the frequency of words
{
    write_with_of_stream(output_file, "", false);   // Clear the output file
    std::vector<std::pair<std::string, int>> pairs; // Create a vector of pairs to store the word frequency
    for (const auto &item : wordFrequency)          // Iterate over the word frequency map
    {
        pairs.push_back(item);
    }
    std::sort(pairs.begin(), pairs.end()); // Sort the word frequency vector
    for (const auto &pair : pairs)         // Iterate over the sorted word frequency vector
    {
        std::string result = pair.first + ",";           // Append the word to the result string
        result += std::to_string(pair.second) + '\n';    // Append the word and its frequency to the result string
        write_with_of_stream(output_file, result, true); // Write the word frequency to the output file
    }
}

void client() // Create a client
{
    int client_sock_fd = connect_to_server(); // Create a client socket and connect that to the server address
    request_words(client_sock_fd);            // Send a request for words to a client
    print_word_freq();                        // Print the fequency of words
}

int main()
{
    read_config(); // read config.json
    client();      // create a client
}
