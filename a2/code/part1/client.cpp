// https://medium.com/@togunchan/getting-started-with-socket-programming-on-macos-building-a-simple-tcp-server-in-c-c39c06df3749

#include <iostream>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <unistd.h>

#define PORT 3000

int main()

{
    int client_sock_fd = socket(AF_INET, SOCK_STREAM, 0);

    if (client_sock_fd == -1)
    {
        perror("Socker creation failed");
        exit(EXIT_FAILURE);
    }
    sockaddr_in address;
    int address_len = sizeof(address);
    address.sin_family = AF_INET;
    address.sin_port = htons(PORT);
    address.sin_addr.s_addr = INADDR_ANY; // connecting to any IPaddress
    if (connect(client_sock_fd, (struct sockaddr *)&address, sizeof(address)) < 0)
    {
        std::cout << "Connection Failed" << std::endl;
        return -1;
    }

    std::cout << "Connected to server" << std::endl;
    close(client_sock_fd);
    return 0;
}
