// https://medium.com/@togunchan/getting-started-with-socket-programming-on-macos-building-a-simple-tcp-server-in-c-c39c06df3749
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
#include "json.hpp"

// global variables
int port;
std::string ip_address;
int offset;
int words_per_packet;
int num_clients;
const int BUFFER_SIZE = 1024;

// Word Frequency map
std::map<std::string, int> wordFrequency;

void read_config()
{
    try
    {
        // Open the config file
        std::ifstream file("config.json");
        nlohmann::json config;
        file >> config;

        // Access data from the JSON
        port = config["server_port"];
        ip_address = config["server_ip"];
        offset = config["k"];
        words_per_packet = config["p"];
        num_clients = config["num_clients"];

        // input = config["input_file"];
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
    std::cout << "Connected to server" << std::endl;
    return client_sock_fd;
}
void count_word(const std::string &word)
{
    if (word != "\n" && word != "EOF") // check this exactly
    {
        wordFrequency[word]++;
    }
}

std::string process_packet(std::string packet_data)
{

    std::vector<std::string> words;
    std::istringstream iss(packet_data);
    std::string token;

    while (iss.good())
    {
        if (std::getline(iss, token, ','))
        {
            // Remove commas from token
            token.erase(std::remove(token.begin(), token.end(), ','), token.end());

            // Further split by newline if present
            std::istringstream line_stream(token);
            std::string subtoken;
            while (std::getline(line_stream, subtoken))
            {
                // Remove commas from subtoken
                subtoken.erase(std::remove(subtoken.begin(), subtoken.end(), ','), subtoken.end());

                if (!subtoken.empty())
                {
                    words.push_back(subtoken);
                }
            }
        }
    }

    for (const auto &w : words)
    {
        count_word(w);
    }

    if (!words.empty())
    {
        std::string lastWord = words.back();
        return lastWord;
    }
    else
    {
        return ""; // Return empty string if no words were found
    }
}

void request(int client_sock_fd)
{
    // Buffer array to read
    char buffer[BUFFER_SIZE] = {0};

    // Last word
    std::string lastWord;
    bool endOfFile = false;

    // Send the requests until u recieve an EOF
    while (!endOfFile)
    {
        // Clear the buffer
        memset(buffer, 0, BUFFER_SIZE);

        // Converting offset to the required api level syntax
        std::string request = std::to_string(offset) + "\n";

        // Sending the request

        // client_sock_fd: This is the first argument to send(). It's a file descriptor representing the client socket to which the data will be sent.
        // request.c_str(): This is the second argument. It's the buffer containing the data to be sent. Here, request appears to be a string object (likely std::string), and c_str() returns a pointer to a null-terminated character array (C-style string) containing the string's data.
        // request.length(): This is the third argument, specifying the number of bytes to send from the buffer. It's using the length() method of the string object to get the exact length of the string.
        // 0: This is the fourth argument, which represents flags. In this case, no special flags are being used (0 means default behavior).
        if (send(client_sock_fd, request.c_str(), request.length(), 0) < -1)
        {
            perror("Client request failed");
            exit(EXIT_FAILURE);
        }

        // Read a packet into buffer
        int valread = read(client_sock_fd, buffer, BUFFER_SIZE);
        if (valread < 0)
        {
            perror("Error reading from server");
            exit(EXIT_FAILURE);
        }

        // if offset is greater than number of words or failure to read
        if (valread <= 0 || strcmp(buffer, "$$\n") == 0)
        {
            endOfFile = true;
            break;
        }

        // Process a packet
        std::string packet_data(buffer);
        std::string last_word = process_packet(packet_data);
        // packet_data.pop_back(); // Remove newline

        // std::cout << word << std::endl;
        if (last_word == "EOF")
        {
            endOfFile = true;
            break;
        }
        else
        {
            offset += words_per_packet;
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
    write_with_of_stream("output.txt", "", false);
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
        write_with_of_stream("output.txt", result, true);
    }
}

void client()
{
    // Create a client socket and connect that to the server address
    int client_sock_fd = connect_to_server();

    // Send a request for words to a client
    request(client_sock_fd);

    // Print the fequency of words
    print_word_freq();

    std::cout << "Server disconnected" << std::endl;
}

int main()

{
    // Read config files
    read_config();

    // Create a client
    client();

    return 0;
}
