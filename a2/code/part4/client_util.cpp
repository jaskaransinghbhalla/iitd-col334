#include "client_util.h"
#include "json.hpp"
#include <algorithm>
#include <arpa/inet.h>
#include <cstring>
#include <fstream>
#include <iostream>
#include <netdb.h>
#include <sstream>
#include <sys/socket.h>
#include <unistd.h>

const int BUFFER_SIZE = 1024;

std::string OUTPUT_FILE = "output";
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
int connect_to_server()
{
    int client_sock_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (client_sock_fd == -1)
    {
        perror("Socket creation failed");
        exit(EXIT_FAILURE);
    }

    sockaddr_in address;
    address.sin_family = AF_INET;
    address.sin_port = htons(port);

    if (ip_address == "0.0.0.0" || ip_address == "INADDR_ANY")
    {
        address.sin_addr.s_addr = INADDR_ANY;
    }
    else
    {
        if (inet_pton(AF_INET, ip_address.c_str(), &address.sin_addr) <= 0)
        {
            std::cerr << "Invalid address/ Address not supported" << std::endl;
            exit(EXIT_FAILURE);
        }
    }

    if (connect(client_sock_fd, (struct sockaddr *)&address, sizeof(address)) < 0)
    {
        perror("Connection failed");
        exit(EXIT_FAILURE);
    }

    std::cout << "Connected to server: " << ip_address << ":" << port << std::endl;
    return client_sock_fd;
}

void count_word(const std::string &word, std::map<std::string, int> &wordFrequency)
{
    std::string s = "";
    s += EOF;
    if (word != "\n" && word != s)
    {
        wordFrequency[word]++;
    }
}

std::string process_packet(const std::string &packet_data, std::map<std::string, int> &wordFrequency)
{
    std::vector<std::string> words;
    std::istringstream iss(packet_data);
    std::string word;

    while (std::getline(iss, word, ','))
    {
        word.erase(0, word.find_first_not_of(" \t\n\r\f\v"));
        word.erase(word.find_last_not_of(" \t\n\r\f\v") + 1);
        if (!word.empty())
        {
            words.push_back(word);
        }
    }

    for (const auto &w : words)
    {
        count_word(w, wordFrequency);
    }

    return words.empty() ? "" : words.back();
}

void request_words(int client_sock_fd, ClientInfo *client_info)
{
    char buffer[BUFFER_SIZE] = {0};

    while (!client_info->is_done.load())
    {
        // Temp code
        std::ostringstream oss;
        oss << pthread_self();

        // Request
        do
        {
            if (!client_info->is_processing)
            {
                std::string req_payload = std::to_string(client_info->offset) + "\n";
                int s = send(client_sock_fd, req_payload.c_str(), req_payload.length(), 0);
                if (s < -1)
                {
                    perror("Client request failed");
                    exit(EXIT_FAILURE);
                }
                
                if (pthread_mutex_trylock(&client_info->client_mutex) != 0)
                {
                    continue;
                }
                client_info->is_processing = true;
                break;
            }

        } while (true);
        // pthread_mutex_unlock(&client_info->client_mutex);
        std::cout << "Request Sent : " << client_info->client_id << " " << oss.str() << " " << client_info->offset << std::endl;

        // Response

        std::cout << "Processing Response : " << client_info->client_id << " " << oss.str() << " " << client_info->offset << std::endl;

        if (strcmp(buffer, "$$\n") == 0)
        {
            break;
        }
        int word_count = 0;
        std::string accumulated_data;

        while (word_count < num_word_per_request)
        {
            char buffer_temp[2] = {0};
            int valread = recv(client_sock_fd, buffer_temp, 1, 0);

            if (valread < 0)
            {
                perror("Error reading from server");
                exit(EXIT_FAILURE);
            }

            if (*buffer_temp == '\n')
            {
                std::cout << "Packet Proccesed : " << client_info->client_id << " " << oss.str() << " " << client_info->offset << std::endl;
                std::string last_word = process_packet(accumulated_data, client_info->wordFrequency);
                std::string s = "";
                s += EOF;
                if (last_word == s)
                {
                    client_info->eof = true;
                    client_info->is_done.store(true);
                    std::cout << "EOF Reached : " << client_info->client_id << " " << oss.str() << " " << client_info->offset << std::endl;

                    break;
                }

                word_count += words_per_packet;
                accumulated_data = "";
            }

            else
            {
                accumulated_data += buffer_temp[0];
            }
        }

        if (!client_info->eof)
        {

            client_info->offset += num_word_per_request;
            std::cout << "Offset Updated : " << client_info->client_id << " " << oss.str() << " " << client_info->offset << std::endl;
        }
        else
        {
            break;
        }
        client_info->is_processing = false;
        pthread_mutex_unlock(&client_info->client_mutex);
        std::cout << "Reponse Processed : " << client_info->client_id << " " << oss.str() << " " << std::endl;
    }
    close(client_sock_fd);
}

void print_word_freq(const ClientInfo *client_info)
{
    std::string client_output_file = OUTPUT_FILE + "_" + std::to_string(client_info->client_id) + ".txt";
    write_with_of_stream(client_output_file, "", false);

    std::vector<std::pair<std::string, int>> pairs;
    for (const auto &item : client_info->wordFrequency)
    {
        pairs.push_back(item);
    }

    std::sort(pairs.begin(), pairs.end());

    for (const auto &pair : pairs)
    {
        std::string result = pair.first + "," + std::to_string(pair.second) + '\n';
        write_with_of_stream(client_output_file, result, true);
    }
}

void *client_thread(void *arg) // Client thread function
{
    ClientInfo *client_info = static_cast<ClientInfo *>(arg); // Cast argument to ClientInfo pointer

    std::cout << "Client " << client_info->client_id << " is starting..." << std::endl; // Client Started

    int client_sock_fd = connect_to_server();   // Connect to server
    request_words(client_sock_fd, client_info); // Request words from server
    print_word_freq(client_info);               // Print word frequency

    std::cout << "Client " << client_info->client_id << " has finished." << std::endl; // Client Finished
    pthread_exit(nullptr);                                                             // Exit thread
}

void *client_thread_rogue(void *arg) // Rogue client thread function
{
    ClientInfo *client_info = static_cast<ClientInfo *>(arg); // Cast argument to ClientInfo pointer

    // Write to rogue output file
    // std::ostringstream oss;
    // oss << pthread_self();
    // std::string rogue_output_file = OUTPUT_FILE + "_rogue_" + std::to_string(client_info->client_id) + "_" + oss.str() + "_.txt";

    int client_sock_fd = connect_to_server();   // Connect to server
    request_words(client_sock_fd, client_info); // Request words from server

    if (!client_info->is_done.load()) // Rogue client not started
    {
        print_word_freq(client_info); // Print word frequency
        std::cout << "Printing word frequency for rogue client " << client_info->client_id << std::endl;
        client_info->is_done.store(true); // Set is_done flag to true
    }

    // write_with_of_stream(rogue_output_file, client_info->is_done.load() ? "true" : "false");                                      // Rogue client started
    // write_with_of_stream(rogue_output_file, "Rogue client " + std::to_string(client_info->client_id) + " has finished.\n", true); // Rogue client finished

    pthread_exit(nullptr); // Exit thread
}