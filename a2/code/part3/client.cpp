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

// Global variables

int protocol; // Protocol to be used

int num_clients;          // Number of clients to be created
int num_word_per_request; // K
int port;                 // Port number of the server
int words_per_packet;     // P
std::string ip_address;   // IP address of the server
int time_slot_len;

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
        time_slot_len = config["T"];
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
    client_info->time_slot_len = time_slot_len;               // Set time slot length
    client_info->num_clients = num_clients;                   // Set number of clients
    client_info->latest_request_sent_timestamp = 0;           // Set latest request timestamp to 0
}

void handle_clients(int num_clients, int protocol) // Create threads for num clients
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

int main(int argc, char *argv[]) // Main function
{
    read_config();                 // Read configuration file
    protocol = std::stoi(argv[1]); // Set protocol to the first argument
    if (protocol == 0)
    {
        std::cout << "Slotted Aloha" << std::endl;
    }
    else if (protocol == 1)
    {
        std::cout << "Binary Exponential Backoff" << std::endl;
    }
    else if (protocol == 2)
    {
        std::cout << "Sensing and BEB" << std::endl;
    }
    else
    {
        std::cout << "Invalid protocol" << std::endl;
        return 1;
    }

    handle_clients(num_clients, protocol); // Create threads for num clients
    return 0;                    // Exit the program
}
// {
//     protocol = argv[1];
//     // auto start_time = std::chrono::high_resolution_clock::now();                                  // Start timing
//     read_config();                                                                                // Read configuration file
//     handle_clients(num_clients);                                                                  // Create threads for num clients
//     // auto end_time = std::chrono::high_resolution_clock::now();                                    // End timing
//     // auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time); // Calculate duration
//     // std::cout << "Execution time: " << duration.count() << " milliseconds" << std::endl;          // Log the duration
//     return 0;                                                                                     // Exit the program
// }