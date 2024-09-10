// Server

// Packages
#include <arpa/inet.h>  // Provides functions for manipulating IP addresses (like inet_addr)
#include <fstream>      // Provides file stream classes for reading/writing files
#include <iostream>     // Provides input/output stream objects like cin, cout, cerr
#include <netdb.h>      // Provides functions for network address and service translation
#include <netinet/in.h> // Provides Internet address family structures and constants
#include <sys/socket.h> // Includes core functions and structures for socket programming
#include <unistd.h>     // Provides POSIX operating system API like close()

// read from config
int port;
std::string input_file;
std::string ip_address;
int words_per_packet;

const int BUFFER_SIZE = 1024;
std::vector<std::string> words;

void read_config()
{
    // open config as txt
    std::ifstream config_file("config_server.txt");

    if (config_file.is_open())
    {
        // Read the values from the file
        config_file >> port;
        config_file >> ip_address;
        config_file >> input_file;
        config_file >> words_per_packet;
        // Close the file
        config_file.close();
    }
    else
    {
        std::cerr << "Unable to open config.txt" << std::endl;
    }
}

void loadWords(const std::string &filename)
{
    std::ifstream file(filename);
    std::string word;
    while (std::getline(file, word, ','))
    {
        words.push_back(word);
    }
    words.push_back("EOF");
}

void handleClient(int client_socket)
{
    char buffer[BUFFER_SIZE] = {0};
    while (true)
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

        if (offset >= words.size())
        {
            // If the offset is too large, sends "$$\n" to the client, indicating an invalid offset
            send(client_socket, "$$\n", 3, 0);
            break;
        }

        // If the offset is valid, enter this block to send words to the client
        else
        {

            // std::cout << "Sending data to client" << std::endl;
            // Loops up to 10 times or until the end of the word list is reached
            // for (int i = 0; offset + i < words.size();)
            // {
            // Prepares a response string with a word and a newline character

            std::string response;
            for (int j = 0; j < words_per_packet && offset + j < words.size(); j++)
            {
                response = response + words[offset + j];
                response = response + ",";
            }

            // End of packet
            if (!response.empty())
            {
                response.pop_back();
                response = response + "\n";
            }

            // std::cout << response;

            // Sends the response string to the client.
            send(client_socket, response.c_str(), response.length(), 0);
            // }
        }
    }
    close(client_socket);
    std::cout << "Connection closed" << std::endl;
}

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
    std::cout << "Server listening on port " << port << std::endl;

    int client_socket;

    while (true)
    {
        if ((client_socket = accept(server_socket_fd, reinterpret_cast<sockaddr *>(&address), (socklen_t *)&address_len)) < 0)
        {
            perror("accept");
            exit(EXIT_FAILURE);
        }

        std::cout << "Client connected" << std::endl;
        handleClient(client_socket);
    }
    close(server_socket_fd);
}

int main()

{
    // Reading configuration
    read_config();

    // Loading the words from the file
    loadWords(input_file);

    // Create a server
    server();
    return 0;
}