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
#include <fstream>
#include <sstream>

// global variables
int port;
std::string ip_address;
int offset;
const int BUFFER_SIZE = 1024;

void read_config()
{

    // Open the config file
    std::ifstream config_file("config_client.txt");

    if (config_file.is_open())
    {
        // Read the values from the file
        config_file >> port;
        config_file >> ip_address;
        config_file >> offset;

        // Close the file
        config_file.close();

        // Print the values to verify
        std::cout << "Port: " << port << std::endl;
        std::cout << "IP Address: " << ip_address << std::endl;
    }
    else
    {
        std::cerr << "Unable to open config.txt" << std::endl;
    }
}

// Word Frequency mapƒ
std::map<std::string, int> wordFrequency;

void writeWithOfstream(const std::string &filename, const std::string &content, bool append = false)
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

void countWord(const std::string &word)
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
        countWord(w);
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
        std::string result = pair.first + ",";
        result += std::to_string(pair.second) + '\n';
        writeWithOfstream("output.txt", result, true);
    }
}

int main()

{
    read_config();
    writeWithOfstream("output.txt", "", false);
    // Client-side socket
    int client_sock_fd = socket(AF_INET, SOCK_STREAM, 0);

    // Check for successfull creation of client socket
    if (client_sock_fd == -1)
    {
        perror("Socker creation failed");
        exit(EXIT_FAILURE);
    }

    // address definitions for client-side socket
    sockaddr_in address;
    int address_len = sizeof(address);
    if (ip_address == "0.0.0.0" || ip_address == "INADDR_ANY")
    {
        // If the config specifies 0.0.0.0 or INADDR_ANY, use INADDR_ANY
        address.sin_addr.s_addr = INADDR_ANY;
    }
    else
    {
        // Otherwise, use the IP address from the config file
        if (inet_pton(AF_INET, ip_address.c_str(), &address.sin_addr) <= 0)
        {
            std::cerr << "Invalid address/ Address not supported" << std::endl;
            return 1;
        }
    } // connecting to server on any IP address
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

    // std::cout << "Read offset set to " << offset << std::endl;

    // Buffer array to read
    char buffer[BUFFER_SIZE] = {0};
    std::string lastWord;

    while (true)
    {
        // converting offset to the required api level syntax
        std::string request = std::to_string(offset) + "\n";

        // std::cout << "Request data from server..." << std::endl;

        // sending the request
        // client_sock_fd: This is the first argument to send(). It's a file descriptor representing the client socket to which the data will be sent.
        // request.c_str(): This is the second argument. It's the buffer containing the data to be sent. Here, request appears to be a string object (likely std::string), and c_str() returns a pointer to a null-terminated character array (C-style string) containing the string's data.
        // request.length(): This is the third argument, specifying the number of bytes to send from the buffer. It's using the length() method of the string object to get the exact length of the string.
        // 0: This is the fourth argument, which represents flags. In this case, no special flags are being used (0 means default behavior).
        if (send(client_sock_fd, request.c_str(), request.length(), 0) < -1)
        {
            perror("Client request failed");
            exit(EXIT_FAILURE);
        }
        else
        {
            // std::cout << "Request for data sent" << std::endl;
        }

        bool endOfFile = false;

        while (true)
        {

            // clear the buffer
            memset(buffer, 0, BUFFER_SIZE);

            // read into buffer
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

            std::string packet_data(buffer);
            // packet_data.pop_back(); // Remove newline

            // std::cout << ++packet << " " << packet_data << std::endl;

            std::string last_word = process_packet(packet_data);

            // std::cout << word << std::endl;
            if (last_word == "EOF")
            {
                endOfFile = true;
                break;
            }
        }

        if (endOfFile)
        {
            break;
        }
    }

    close(client_sock_fd);
    printWordFrequency();
    return 0;
}
