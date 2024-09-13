// Server

// Packages
#include "json.hpp"
#include <arpa/inet.h>  // Provides functions for manipulating IP addresses (like inet_addr)
#include <fstream>      // Provides file stream classes for reading/writing files
#include <iostream>     // Provides input/output stream objects like cin, cout, cerr
#include <netdb.h>      // Provides functions for network address and service translation
#include <netinet/in.h> // Provides Internet address family structures and constants
#include <sys/socket.h> // Includes core functions and structures for socket programming
#include <unistd.h>     // Provides POSIX operating system API like close()

// Global variables
int num_clients = 1;
int num_word_per_request;
int port;
int words_per_packet;
std::string input_file;
std::string ip_address;
std::vector<std::string> words;

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
        input_file = config["input_file"];
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

void read_words() // Read the words from the input file
{
    std::ifstream file(input_file);       // Open the input file
    std::string word;                     // Variable to store the word read from the file
    while (std::getline(file, word, ',')) // Read from the input stream file until it encounters the delimiter ','
    {
        words.push_back(word);
    }
    std::string s = ""; // Add EOF to the end of the word list
    s += EOF;           // EOF is a special character that marks the end of the file
    words.push_back(s); // Add EOF to the end of the word list
}

void handle_client(int client_socket) // Handle the client request
{
    char buffer[BUFFER_SIZE] = {0}; // Buffer to store the data received from the client
    int total_words_sent = 0;       // Variable to keep track of the total number of words sent to the client

    while (total_words_sent != words.size())
    {
        memset(buffer, 0, BUFFER_SIZE);                         // Clear the buffer
        int valread = read(client_socket, buffer, BUFFER_SIZE); // Read data from the client socket into the buffer
        if (valread <= 0)                                       // If the read operation fails or the client disconnects
            break;
        int offset = std::stoi(buffer); // Convert the buffer data to an integer to get the offset value

        // Invalid Offset
        if (offset >= words.size()) // Checks if the requested offset is beyond the end of the word list
        {
            send(client_socket, "$$\n", 3, 0); // If the offset is too large, sends "$$\n" to the client, indicating an invalid offset
            break;
        }

        // Valid offset
        bool eof = false; // Variable to check if the end of the file has been reached
        for (int word_count = 0; word_count < num_word_per_request && !eof;)
        {
            // Packet
            std::string packet;
            for (int packet_count = 0; packet_count < words_per_packet && word_count < num_word_per_request && !eof; packet_count++, word_count++, total_words_sent++)
            {
                std::string word = words[offset + word_count];
                packet += word;
                packet += ",";

                std::string s = "";
                s += EOF;
                if (word == s)
                {
                    eof = true;
                    break;
                }
            }
            packet.pop_back();                                       // Remove the last comma from the packet
            packet = packet + "\n";                                  // Add a newline character at the end of the packet
            send(client_socket, packet.c_str(), packet.length(), 0); // Send the packet to the client
        }
    }
}

void handle_clients(int server_socket_fd, sockaddr_in address, int address_len)
{
    for (int i = 0; i < num_clients; i++) // Loop to handle multiple clients
    {
        int client_socket = accept(server_socket_fd, reinterpret_cast<sockaddr *>(&address), reinterpret_cast<socklen_t *>(&address_len)); // Accepting the client
        if (client_socket < 0)
        {
            perror("accept failed");
            exit(EXIT_FAILURE);
        }
        std::cout << "Client connected" << std::endl;    // Client connected message
        handle_client(client_socket);                    // Handling the client
        close(client_socket);                            // Closing the client socket
        std::cout << "Client Disconnected" << std::endl; // Client disconnected message
    }
}

void server()
{
    // Sever Socket

    // - AF_INET: Indicates that the socket will use the IPv4 protocol.
    // - SOCK_STREAM: Specifies the type of socket. This type provides connection-oriented, reliable, and order-preserving data transmission.
    // - 0: This parameter specifies the protocol to be used, and TCP (the default protocol) is selected.
    int server_socket_fd = socket(AF_INET, SOCK_STREAM, 0); // Creating a socket
    if (server_socket_fd == -1)                             // Check if the socket was created successfully or not, if it is not created it should return -1
    {
        perror("socket creation failure");
        exit(EXIT_FAILURE);
    }

    // Server Address

    sockaddr_in address;               // sockaddr_in is a structure used to represent an Internet Protocol version 4(IPv4)socket address.
    int address_len = sizeof(address); // - address_len: This variable stores the size of the address structure.
    address.sin_family = AF_INET;      // - sin_family: This member specifies the address family. AF_INET is used for IPv4.
    if (ip_address == "0.0.0.0" || ip_address == "INADDR_ANY")
    {
        address.sin_addr.s_addr = INADDR_ANY; // - sin_addr.s_addr: This member holds the IP address.
    }
    else
    {
        // Otherwise, use the IP address from the config file
        if (inet_pton(AF_INET, ip_address.c_str(), &address.sin_addr) <= 0)
        {
            std::cerr << "Invalid address/ Address not supported" << std::endl;
        }
    }
    address.sin_port = htons(port); // - sin_port: Specifies the port number as a 16-bit integer.

    // Binding

    // The part where we bind the socket to an IP address and a port
    // Binding a socket means associating the socket with a specific address and port number on the local machine.
    // It tells the operating system that you want to receive incoming connections on a specific IP address and port combination
    // Note: If you don't bind a socket explicitly, the system will assign a random port when you start listening or connecting.
    if (bind(server_socket_fd, reinterpret_cast<sockaddr *>(&address), address_len) < 0)
    {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }

    // Listening

    // Listening on a socket means configuring the socket to accept incoming connection requests.
    // It prepares the socket to receive client connections, creating a queue for incoming connection requests.
    // SOMACONN You specify a backlog parameter, which defines the maximum length of the queue for pending connections
    if (listen(server_socket_fd, SOMAXCONN) < 0)
    {
        perror("listen failed");
        exit(EXIT_FAILURE);
    }
    std::cout << "Server listening on :" << ip_address << ":" << port << std::endl;

    // Handling Clients
    handle_clients(server_socket_fd, address, address_len); // Handle  clients
    close(server_socket_fd);                                // Close the server socket
    return;
}

int main()

{
    read_config(); // Reading configuration
    read_words();  // Loading the words from the file
    server();      // Initiazling the server and start handling client requests
}