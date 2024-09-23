// Packages
#include "json.hpp"      // JSON library
#include "client_util.h" // Client utility functions
#include <cstdlib>       // C standard library
#include <fstream>       // File stream
#include <iostream>      // Input/output stream
#include <pthread.h>     // POSIX threads
#include <unistd.h>      // POSIX operating system API
#include <vector>        // Vector
#include <chrono>        // Add this for timing functionality

int num_clients;          // Number of clients to be created
int num_word_per_request; // K
int port;                 // Port number of the server
int words_per_packet;     // P
std::string ip_address;   // IP address of the server

void read_config() // Read configuration file
{
    try
    {
        // Open configuration file
        std::ifstream file("config.json");
        nlohmann::json config;
        file >> config;

        // Read configuration parameters
        num_clients = config["num_clients"];
        ip_address = config["server_ip"];
        num_word_per_request = config["k"];
        port = config["server_port"];
        words_per_packet = config["p"];
    }
    catch (nlohmann::json::exception &e)
    {
        std::cerr << "JSON parsing error: " << e.what() << std::endl;
    }
}

void intialize_client(int client_id, ClientInfo *client_info) // Initialize client information
{
    client_info->client_id = client_id;                       // Set client ID
    client_info->offset = 0;                                  // Set offset to 0
    client_info->wordFrequency.clear();                       // Clear word frequency map
    client_info->num_word_per_request = num_word_per_request; // Set number of words per request
    client_info->port = port;                                 // Set server port
    client_info->words_per_packet = words_per_packet;         // Set words per packet
    client_info->ip_address = ip_address;                     // Set server IP address
}

void handle_clients(int num_clients) // Create threads for num clients
{
    std::vector<pthread_t> threads(num_clients);       // Vector to store thread IDs
    std::vector<ClientInfo> client_infos(num_clients); // Vector to store client information

    // Create threads for each client
    for (int i = 0; i < num_clients; ++i)
    {
        intialize_client(i + 1, &client_infos[i]);                                          // Initialize client information
        int result = pthread_create(&threads[i], nullptr, client_thread, &client_infos[i]); // Create a new thread for the client
        if (result != 0)                                                                    // Check if thread creation was successful
        {
            std::cerr << "Error creating thread for client " << i + 1 << std::endl;
            exit(EXIT_FAILURE);
        }
    }

    for (int i = 0; i < num_clients; ++i) // Wait for all threads to complete
    {
        pthread_join(threads[i], nullptr); // Wait for the thread to finish
    }

    std::cout << "All clients have finished." << std::endl;
}

int main()
{
    read_config();                                                                                // Read configuration file
    handle_clients(num_clients);                                                                  // Create threads for num clients
    return 0;                                                                                     // Exit the program
}