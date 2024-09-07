// https://medium.com/@togunchan/getting-started-with-socket-programming-on-macos-building-a-simple-tcp-server-in-c-c39c06df3749

#include <iostream>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <unistd.h>

int main()

{
    // - AF_INET: Indicates that the socket will use the IPv4 protocol.
    // - SOCK_STREAM: Specifies the type of socket. This type provides connection-oriented, reliable, and order-preserving data transmission.
    // - 0: This parameter specifies the protocol to be used, and TCP (the default protocol) is selected.
    int listening = socket(AF_INET, SOCK_STREAM, 0);

    // if listening is negative creation of server fails
    if (listening == -1)
    {
        std::cerr << "Can't create a socket! Quitting…" << std::endl;
        return -1;
    }
}
