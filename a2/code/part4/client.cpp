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

// Controllers
int ROGUE_CLIENT_EXISTS = 0;
int ROGUE_THREADS = 2;

// Global variables
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
    client_info->ip_address = ip_address;                     // Set server IP address
    client_info->is_done = false;                             // Set is_done flag to false
    client_info->is_processing= false;                             // Set is_done flag to false
    client_info->num_word_per_request = num_word_per_request; // Set number of words per request
    client_info->offset = 0;                                  // Set offset to 0
    client_info->port = port;                                 // Set server port
    client_info->wordFrequency.clear();                       // Clear word frequency map
    client_info->words_per_packet = words_per_packet;         // Set words per packet
    pthread_mutex_init(&client_info->client_mutex, nullptr);  // Initialize client mutex
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

void handle_clients_rogue() // Create threads for rogue client
{

    std::vector<pthread_t> threads(num_clients);         // Vector to store thread IDs
    std::vector<ClientInfo> client_infos(num_clients);   // Vector to store client information
    std::vector<pthread_t> rogue_threads(ROGUE_THREADS); // Vector to store thread IDs for rogue client

    // Create threads for each client except rogue client
    for (int i = 0; i < num_clients - 1; ++i)
    {
        intialize_client(i + 1, &client_infos[i]);                                          // Initialize client information
        int result = pthread_create(&threads[i], nullptr, client_thread, &client_infos[i]); // Create a new thread for the client
        if (result != 0)                                                                    // Check if thread creation was successful
        {
            std::cerr << "Error creating thread for client " << i + 1 << std::endl;
            exit(EXIT_FAILURE);
        }
    }

    intialize_client(num_clients - 1, &client_infos[num_clients - 1]); // Initialize client information
    ClientInfo &rogue_client_info = client_infos[num_clients - 1];     // Get rogue client information
    // rogue_client_info.is_done = false;                                 // Set is_done flag to false
    for (int i = 0; i < ROGUE_THREADS; ++i)
    {
        int result = pthread_create(&rogue_threads[i], nullptr, client_thread_rogue, &rogue_client_info); // Create a new thread for the client
        if (result != 0)                                                                                  // Check if thread creation was successful
        {
            std::cerr << "Error creating thread for rogue client" << std::endl;
            exit(EXIT_FAILURE);
        }
    }

    for (int i = 0; i < num_clients; ++i) // Wait for all threads to complete
    {
        pthread_join(threads[i], nullptr); // Wait for the thread to finish
    }
    for (int i = 0; i < ROGUE_THREADS; ++i)
    {
        pthread_join(rogue_threads[i], nullptr); // Wait for the thread to finish
    }

    std::cout << "All clients have finished." << std::endl;
}

int main(int argc, char *argv[])
{
    read_config();                            // Read configuration file
    ROGUE_CLIENT_EXISTS = std::stoi(argv[1]); // Check if rogue client exists

    if (ROGUE_CLIENT_EXISTS == 1)
    {
        std::cout << "Rogue client exists" << std::endl;
        handle_clients_rogue();
    }
    else
    {
        std::cout << "Rogue client does not exist" << std::endl;
        handle_clients(num_clients); // Create threads for num clients
    }

    return 0; // Exit the program
}