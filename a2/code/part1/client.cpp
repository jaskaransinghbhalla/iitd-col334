// https://medium.com/@togunchan/getting-started-with-socket-programming-on-macos-building-a-simple-tcp-server-in-c-c39c06df3749

#include <iostream>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <unistd.h>

#include <cstring>
#include <algorithm>
#include <map>
#include <string>

#define PORT 3000 // pre-defined ip and port ??
const int BUFFER_SIZE = 1024;
std::map<std::string, int> wordFrequency;

void countWord(const std::string &word)
{
    if (word != "EOF")
    {
        wordFrequency[word]++;
    }
}

void printWordFrequency()
{
    std::vector<std::pair<std::string, int>> pairs;
    for (const auto &item : wordFrequency)
    {
        pairs.push_back(item);
    }
    std::sort(pairs.begin(), pairs.end());

    for (const auto &pair : pairs)
    {
        std::cout << pair.first << ", " << pair.second << std::endl;
    }
}

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
    if (connect(client_sock_fd, (struct sockaddr *)&address, address_len) < 0)
    {
        std::cout << "Connection Failed" << std::endl;
        return -1;
    }

    std::cout << "Connected to server" << std::endl;

    int offset = 1;
    char buffer[BUFFER_SIZE] = {0};
    std::string lastWord;

    while (true)
    {
        std::string request = std::to_string(offset) + "\n";
        send(client_sock_fd, request.c_str(), request.length(), 0);

        bool endOfFile = false;
        for (int i = 0; i < 10; ++i)
        {
            memset(buffer, 0, BUFFER_SIZE);
            int valread = read(client_sock_fd, buffer, BUFFER_SIZE);
            if (valread <= 0 || strcmp(buffer, "$$\n") == 0)
            {
                endOfFile = true;
                break;
            }

            std::string word(buffer);
            word.pop_back(); // Remove newline
            countWord(word);
            lastWord = word;
            offset++;

            if (word == "\n")
            {
                endOfFile = true;
                break;
            }
        }

        if (endOfFile)
            break;
    }

    close(client_sock_fd);
    printWordFrequency();
    return 0;
}
