#include "json.hpp"
#include "client_util.h"
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <pthread.h>
#include <unistd.h>
#include <vector>

int num_clients;

// Read configuration file
void read_config()
{
    try
    {
        std::ifstream file("config.json");
        nlohmann::json config;
        file >> config;

        num_clients = config["num_clients"];
    }
    catch (nlohmann::json::exception &e)
    {
        std::cerr << "JSON parsing error: " << e.what() << std::endl;
    }
}

// Client thread function
void handle_clients(int num_clients)
{
    std::cout << "Number of clients: " << num_clients << std::endl;
    // Vector to store thread IDs
    std::vector<pthread_t> threads(num_clients);

    // Vector to store client information
    std::vector<ClientInfo> client_infos(num_clients);

    // Create threads for each client
    for (int i = 0; i < num_clients; ++i)
    {
        // Initialize client information
        client_infos[i].client_id = i + 1;

        // Create a new thread for the client
        int result = pthread_create(&threads[i], nullptr, client_thread, &client_infos[i]);

        // std::string command = "./launch_client.sh " + std::to_string(i);
        // system(command.c_str());

        // Check if thread creation was successful
        if (result != 0)
        {
            std::cerr << "Error creating thread for client " << i + 1 << std::endl;
            exit(EXIT_FAILURE);
        }
    }

    // Wait for all threads to complete
    for (int i = 0; i < num_clients; ++i)
    {
        pthread_join(threads[i], nullptr);
    }

    std::cout << "All clients have finished." << std::endl;
}

int main()
{
    read_config();
    handle_clients(num_clients);
    return 0;
}