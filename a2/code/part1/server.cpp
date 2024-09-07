// server socket
// Socket
// A socket is an endpoint for communication between two programs running on a network. It's essentially a combination of an IP address and a port number.

#include <iostream>     // input/output
#include <sys/socket.h> // sockets
#include <netdb.h>
#include <unistd.h>

#define PORT 3000

int main()
{

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

    // sockaddr_in is a structure used to represent an Internet Protocol version 4(IPv4)socket address.
    // - sin_family: This member specifies the address family. AF_INET is used for IPv4.
    // - sin_port: Specifies the port number as a 16-bit integer.
    // - sin_addr.s_addr: This member holds the IP address.
    sockaddr_in address;
    int address_len = sizeof(address);
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY; // accepting connections on any ip address
    address.sin_port = htons(PORT);

    // The part where we bind the socket to an IP address and a port
    // Binding a socket means associating the socket with a specific address and port number on the local machine.
    // It tells the operating system that you want to receive incoming connections on a specific IP address and port combination
    // Note: If you don't bind a socket explicitly, the system will assign a random port when you start listening or connecting.
    if (bind(server_socket_fd, reinterpret_cast<sockaddr *>(&address), address_len) < 0)
    {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }

    // Listening on a socket means configuring the socket to accept incoming connection requests.
    // It prepares the socket to receive client connections, creating a queue for incoming connection requests.
    // SOMACONN You specify a backlog parameter, which defines the maximum length of the queue for pending connections
    if (listen(server_socket_fd, SOMAXCONN) < 0)
    {
        perror("listen failed");
        exit(EXIT_FAILURE);
    }
    std::cout << "Server listening on port " << PORT << std::endl;

    int client_socket;

    while (true)
    {
        if ((client_socket = accept(server_socket_fd, reinterpret_cast<sockaddr *>(&address), (socklen_t *)&address_len)) < 0)
        {
            perror("accept");
            exit(EXIT_FAILURE);
        }

        std::cout << "Client connected" << std::endl;

        close(client_socket);
        std::cout << "Connection closed" << std::endl;
    }
    return 0;
}