// Server Code (server.cpp)
#include <iostream>
#include <string>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>

#define PORT 3000
#define BUFFER_SIZE 1024

int main() {
    int server_fd, new_socket;
    sockaddr_in serverAddress;
    int lenServerAddress = sizeof(serverAddress);
    char buffer[BUFFER_SIZE] = {0};

    // Creating socket file descriptor
    // if ((server_fd = socket(AF_INET, SOCK_DGRAM, 0)) == 0) {
    //     perror("socket failed");
    //     exit(EXIT_FAILURE);
    // }

    // // Configuring socket options
    // int opt = 1;
    // if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt))) {
    //     perror("setsockopt");
    //     exit(EXIT_FAILURE);
    // }

    // address.sin_family = AF_INET;
    // address.sin_addr.s_addr = INADDR_ANY;
    // address.sin_port = htons(PORT);

    // // Binding socket to the port
    // if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
    //     perror("bind failed");
    //     exit(EXIT_FAILURE);
    // }

    // if (listen(server_fd, 3) < 0) {
    //     perror("listen");
    //     exit(EXIT_FAILURE);
    // }

    // std::cout << "Server listening on port " << PORT << std::endl;

    // while(true) {
    //     if ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen)) < 0) {
    //         perror("accept");
    //         exit(EXIT_FAILURE);
    //     }

    //     std::cout << "New connection accepted" << std::endl;

    //     while(true) {
    //         memset(buffer, 0, BUFFER_SIZE);
    //         int valread = read(new_socket, buffer, BUFFER_SIZE);
    //         if (valread <= 0) break;

    //         std::cout << "Received: " << buffer << std::endl;
    //         send(new_socket, buffer, strlen(buffer), 0);
    //     }

    //     close(new_socket);
    //     std::cout << "Connection closed" << std::endl;
    // }

    return 0;
}