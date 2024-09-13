// Server

// Packages
#include "json.hpp"
#include <arpa/inet.h>  // Provides functions for manipulating IP addresses (like inet_addr)
#include <fstream>      // Provides file stream classes for reading/writing files
#include <iostream>     // Provides input/output stream objects like cin, cout, cerr
#include <netdb.h>      // Provides functions for network address and service translation
#include <netinet/in.h> // Provides Internet address family structures and constants
#include <sys/socket.h> // Includes core functions and structures for socket programming
#include <unistd.h>     // Provides access to the POSIX operating system API
#include <pthread.h>    // Provides functions for creating and managing threads

// Read from file
int port;
int num_clients = 1;
int words_per_packet;
int num_word_per_request;
std::string input_file;
std::string ip_address;
std::vector<std::string> words;

// Constants
const int BUFFER_SIZE = 1024;

struct thread_data
{
    int client_socket;
};

void read_config()
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

void read_words()
{
    std::ifstream file(input_file);
    std::string word;
    // Read from the input stream file until it encounters the delimiter ',' (
    while (std::getline(file, word, ','))
    {
        words.push_back(word);
    }

    // Add EOF to the end of the word list
    std::string s = "";
    s += EOF;
    words.push_back(s);
}

void handle_client(int client_socket)
{
    char buffer[BUFFER_SIZE] = {0};
    int total_words_sent = 0;
    while (total_words_sent != words.size())
    {
        // It fills the first BUFFER_SIZE bytes of the memory area pointed to by buffer with zeros.
        memset(buffer, 0, BUFFER_SIZE);

        int valread = read(client_socket, buffer, BUFFER_SIZE);
        if (valread <= 0)
            break;

        // Converts the received string (assumed to be a number) to an integer.
        // This offset represents the starting position in the word list requested by the client.

        int offset = std::stoi(buffer);
        // std::cout << "offset is " << offset << std::endl;
        // Checks if the requested offset is beyond the end of the word list

        // Invalid Offset
        if (offset >= words.size())
        {
            // If the offset is too large, sends "$$\n" to the client, indicating an invalid offset
            send(client_socket, "$$\n", 3, 0);
            break;
        }

        // Valid offset
        bool eof = false;
        for (int word_count = 0; word_count < num_word_per_request && !eof;) // Loop to send the requested words to the client
        {

            std::string packet; // Packet to be sent to the client
            for (int packet_count = 0; packet_count < words_per_packet && word_count < num_word_per_request && !eof; packet_count++, word_count++)
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
            packet.pop_back();                                       // Remove the last comma
            packet = packet + "\n";                                  // Add a newline character at the end of the packet
            send(client_socket, packet.c_str(), packet.length(), 0); // Send the packet to the client
        }
    }
}

// Thread function
void *handle_client_thread(void *arg)
{
    struct thread_data *data = (struct thread_data *)arg;
    handle_client(data->client_socket);
    close(data->client_socket);
    delete data;
    pthread_exit(NULL);
}

// Concurrent
void handle_clients(int server_socket_fd, sockaddr_in address, int address_len)
{
    std::vector<pthread_t> threads(num_clients); // Vector to store the thread IDs

    // Loop to accept multiple clients
    for (int i = 0; i < num_clients; i++)
    {
        int client_socket = accept(server_socket_fd, reinterpret_cast<sockaddr *>(&address), reinterpret_cast<socklen_t *>(&address_len)); // Accepting the client
        if (client_socket < 0)                                                                                                             // Checking if the client socket is valid
        {
            perror("accept failed");
            exit(EXIT_FAILURE);
        }

        // Client
        struct thread_data *data = new thread_data; // Create thread data
        data->client_socket = client_socket;        // Assign the client socket to the thread data

        int rc = pthread_create(&threads[i], NULL, handle_client_thread, (void *)data);
        if (rc)
        {
            std::cerr << "Error creating thread: " << rc << std::endl;
            delete data;
            close(client_socket);
        }
    }

    // Wait for all threads to complete
    for (int i = 0; i < num_clients; i++)
    {
        pthread_join(threads[i], NULL);
    }

    return;
}

// Sequential

// void handle_clients(int server_socket_fd, sockaddr_in address, int address_len)
// {
//     std::vector<pthread_t> threads(num_clients); // Vector to store the thread IDs

//     // Loop to accept multiple clients
//     for (int i = 0; i < num_clients; i++)
//     {
//         int client_socket = accept(server_socket_fd, reinterpret_cast<sockaddr *>(&address), reinterpret_cast<socklen_t *>(&address_len)); // Accepting the client
//         if (client_socket < 0)                                                                                                             // Checking if the client socket is valid
//         {
//             perror("accept failed");
//             exit(EXIT_FAILURE);
//         }

//         // Client
//         handle_client(client_socket);

//         close(client_socket);
//     }

//         return;
// }

void server()
{

    // Sever Socket

    // In Unix-like systems, sockets are treated as files, and each is assigned a unique file descriptor (which is just an integer).
    // - AF_INET: Indicates that the socket will use the IPv4 protocol.
    // - SOCK_STREAM: Specifies the type of socket. This type provides connection-oriented, reliable, and order-preserving data transmission.
    // - 0: This parameter specifies the protocol to be used, and TCP (the default protocol) is selected.
    int server_socket_fd = socket(AF_INET, SOCK_STREAM, 0);

    // Check if the socket was created successfully or not, if it is not created it should return -1
    if (server_socket_fd == -1)
    {
        perror("socket creation failure");
        exit(EXIT_FAILURE);
    }

    // Server Address

    // sockaddr_in is a structure used to represent an Internet Protocol version 4(IPv4)socket address.
    // - sin_family: This member specifies the address family. AF_INET is used for IPv4.
    // - sin_port: Specifies the port number as a 16-bit integer.
    // - sin_addr.s_addr: This member holds the IP address.
    sockaddr_in address;
    int address_len = sizeof(address);
    address.sin_family = AF_INET;
    if (ip_address == "0.0.0.0" || ip_address == "INADDR_ANY")
    {
        // std::cout << ip_address;
        // If the config specifies 0.0.0.0 or INADDR_ANY, use INADDR_ANY
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

    address.sin_port = htons(port);

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
    std::cout << "Server listening on " << ip_address << ":" << port << std::endl;

    // hanlde clients
    handle_clients(server_socket_fd, address, address_len);
    close(server_socket_fd);
    return;
}

int main()

{
    // Reading configuration
    read_config();

    // Loading the words from the file
    read_words();

    // Initiazling the server and start handling client requests
    server();
}