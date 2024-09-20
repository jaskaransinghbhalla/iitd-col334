// Server

// Packages
#include "json.hpp"
#include <arpa/inet.h>
#include <fstream>
#include <iostream>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
#include <pthread.h>

// Read from file
int port;
int num_clients = 1;
int words_per_packet;
int num_word_per_request;
std::string input_file;
std::string ip_address;
std::vector<std::string> words;

// Constants
const int BUFFER_SIZE = 1024;

// Client Threads
struct thread_data
{
    int client_socket;
};

// Scheduing
int policy;

struct Request
{
    int client_socket;
    int offset;
};

std::queue<Request> request_queue;
std::queue<int> client_queue;
pthread_mutex_t request_queue_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t request_queue_cond = PTHREAD_COND_INITIALIZER;
pthread_mutex_t client_request_queue_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t client_request_queue_cond = PTHREAD_COND_INITIALIZER;
std::atomic<bool> server_running(true);

///////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////// Functions ////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////

void read_config()
{
    try
    {
        // Open the config file
        std::ifstream file("config.json");
        nlohmann::json config;
        file >> config;

        // Access data from the JSON
        input_file = config["input_file"];
        ip_address = config["server_ip"];
        num_clients = config["num_clients"];
        num_word_per_request = config["k"];
        port = config["server_port"];
        words_per_packet = config["p"];
    }
    catch (nlohmann::json::exception &e)
    {
        std::cerr << "JSON parsing error: " << e.what() << std::endl;
    }
}

void read_words()
{
    std::ifstream file(input_file);
    std::string word;
    // Read from the input stream file until it encounters the delimiter ',' (
    while (std::getline(file, word, ','))
    {
        words.push_back(word);
    }

    // Add EOF to the end of the word list
    std::string s = "";
    s += EOF;
    words.push_back(s);
}

void process_request(const Request &req)
{
    int client_socket = req.client_socket;
    int offset = req.offset;

    // Invalid Offset
    if (offset >= words.size())
    {
        send(client_socket, "$$\n", 3, 0);
        return;
    }

    // Valid offset
    bool eof = false;
    for (int word_count = 0; word_count < num_word_per_request && !eof;)
    {
        std::string packet;
        for (int packet_count = 0; packet_count < words_per_packet && word_count < num_word_per_request && !eof; packet_count++, word_count++)
        {
            std::string word = words[offset + word_count];
            packet += word + ",";

            if (word.length() == 1 && word[0] == EOF)
            {
                eof = true;
                break;
            }
        }
        if (!packet.empty())
        {
            packet.pop_back(); // Remove the last comma
            packet += "\n";
            send(client_socket, packet.c_str(), packet.length(), 0);
        }
    }
}

void *scheduler(void *arg)
{
    while (server_running)
    {
        pthread_mutex_lock(&request_queue_mutex);
        while (request_queue.empty() && server_running)
        {
            pthread_cond_wait(&request_queue_cond, &request_queue_mutex);
        }
        if (!server_running && request_queue.empty())
        {
            pthread_mutex_unlock(&request_queue_mutex);
            break;
        }
        Request req = request_queue.front();
        request_queue.pop();
        std ::cout << "Processing request from client " << req.client_socket << " at offset " << req.offset << std::endl;
        process_request(req);
        pthread_mutex_unlock(&request_queue_mutex);
    }
    return NULL;
}

void *handle_client_fifo(void *arg)
{
    int client_socket = *((int *)arg);
    delete (int *)arg;

    char buffer[BUFFER_SIZE] = {0};
    while (true && client_socket > 0)
    {
        memset(buffer, 0, BUFFER_SIZE);
        int valread = read(client_socket, buffer, BUFFER_SIZE);
        if (valread <= 0)
            break;

        int offset = std::stoi(buffer);

        Request req{client_socket, offset};
        pthread_mutex_lock(&request_queue_mutex);
        std::cout << "Client " << client_socket << " requested offset " << offset << std::endl;
        request_queue.push(req);
        pthread_cond_signal(&request_queue_cond);
        pthread_mutex_unlock(&request_queue_mutex);
    }
    return NULL;
}

void *handle_client_rr(void *arg)
{
    int client_socket = *((int *)arg);
    delete (int *)arg;

    char buffer[BUFFER_SIZE] = {0};
    while (true)
    {

        memset(buffer, 0, BUFFER_SIZE);
        int valread = read(client_socket, buffer, BUFFER_SIZE);
        if (valread <= 0)
            break;
        int offset = std::stoi(buffer);
        // std::cout << "Client " << client_socket << " requested offset " << offset << std::endl;

        Request req{client_socket, offset};
        pthread_mutex_lock(&client_request_queue_mutex);
        // std ::cout << "Client " << client_socket << " is in the queue" << std::endl;
        while (client_queue.front() != client_socket && server_running && request_queue.size() > 0)
        {
            // std ::cout << "Client " << client_socket << " is waiting for its turn" << std::endl;
            pthread_cond_wait(&client_request_queue_cond, &client_request_queue_mutex);
        }
        pthread_mutex_lock(&request_queue_mutex);
        // std ::cout << "Client " << client_socket << " is being served" << std::endl;
        request_queue.push(req);
        pthread_cond_signal(&request_queue_cond);
        pthread_mutex_unlock(&request_queue_mutex);
        client_queue.pop();
        client_queue.push(client_socket);
        pthread_cond_broadcast(&client_request_queue_cond);
        pthread_mutex_unlock(&client_request_queue_mutex);
        if (offset >= words.size())
        {
            break;
        }
    }

    close(client_socket);
    return NULL;
}

// Concurrent
void handle_clients(int server_socket_fd, sockaddr_in address, int address_len)
{

    pthread_t scheduler_thread;                  // Thread for the scheduler
    std::vector<pthread_t> threads(num_clients); // Vector to store the thread IDs for the clients

    pthread_create(&scheduler_thread, NULL, scheduler, NULL); // Create the scheduler thread

    for (int i = 0; i < num_clients; i++) // Loop to accept multiple clients
    {
        int client_socket = accept(server_socket_fd, reinterpret_cast<sockaddr *>(&address), reinterpret_cast<socklen_t *>(&address_len)); // Accepting the client
        if (client_socket < 0)                                                                                                             // Checking if the client socket is valid
        {
            perror("accept failed");
            exit(EXIT_FAILURE);
        }

        // Client
        struct thread_data *data = new thread_data; // Create thread data
        data->client_socket = client_socket;        // Assign the client socket to the thread data
        int rc;
        if (policy == 0)
        {
            rc = pthread_create(&threads[i], NULL, handle_client_fifo, (void *)data);
        }
        else
        {
            client_queue.push(client_socket);
            rc = pthread_create(&threads[i], NULL, handle_client_rr, (void *)data);
        }
        if (rc < 0)
        {
            std::cerr << "Error creating thread: " << rc << std::endl;
            delete data;
            close(client_socket);
        }
    }

    // Wait for all threads to complete
    for (int i = 0; i < num_clients; i++)
    {
        pthread_join(threads[i], NULL);
    }

    server_running = false;
    pthread_cond_signal(&request_queue_cond);
    pthread_join(scheduler_thread, NULL);
    return;
}

void server()
{
    // Sever Socket

    int server_socket_fd = socket(AF_INET, SOCK_STREAM, 0);

    // Check if the socket was created successfully or not, if it is not created it should return -1
    if (server_socket_fd == -1)
    {
        perror("socket creation failure");
        exit(EXIT_FAILURE);
    }

    // Server Address

    sockaddr_in address;
    int address_len = sizeof(address);
    address.sin_family = AF_INET;
    if (ip_address == "0.0.0.0" || ip_address == "INADDR_ANY")
    {
        address.sin_addr.s_addr = INADDR_ANY; // If the config specifies 0.0.0.0 or INADDR_ANY, use INADDR_ANY
    }
    else
    {

        if (inet_pton(AF_INET, ip_address.c_str(), &address.sin_addr) <= 0) // Otherwise, use the IP address from the config file
        {
            std::cerr << "Invalid address/ Address not supported" << std::endl;
        }
    }

    address.sin_port = htons(port);

    // Binding

    if (bind(server_socket_fd, reinterpret_cast<sockaddr *>(&address), address_len) < 0)
    {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }

    // Listening

    if (listen(server_socket_fd, SOMAXCONN) < 0)
    {
        perror("listen failed");
        exit(EXIT_FAILURE);
    }

    std::cout << "Server listening on " << ip_address << ":" << port << std::endl;

    handle_clients(server_socket_fd, address, address_len); // Handling the clients
    close(server_socket_fd);                                // Closing the server socket
    return;
}

int main(int argc, char *argv[])
{
    // Check the scheduling policy
    try
    {
        policy = std::stoi(argv[1]);
    }
    catch (const std::invalid_argument &e)
    {
        std::cerr << "Invalid input. Please enter a number (0, 1, or 2)." << std::endl;
        return 1;
    }
    catch (const std::out_of_range &e)
    {
        std::cerr << "Input out of range. Please enter 0, 1, or 2." << std::endl;
        return 1;
    }

    std::cout << "Scheduling Policy: " << policy << std::endl;

    switch (policy)
    {
    case 0:
        std::cout << "FIFO" << std::endl;
        break;
    case 1:
        std::cout << "Round Robin" << std::endl;
        break;
    case 2:
        std::cout << "Other Policy" << std::endl;
        break;
    default:
        std::cerr << "Invalid policy number. Please use 0, 1, or 2." << std::endl;
        return 1;
    }
    read_config(); // Reading configuration
    read_words();  // Loading the words from the file
    server();      // Initiazling the server and start handling client requests
}