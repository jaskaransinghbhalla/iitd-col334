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

// FIFO
struct FifoRequest
{
    int client_socket;
    int offset;
};
std::queue<FifoRequest> request_queue;
pthread_mutex_t queue_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t queue_cond = PTHREAD_COND_INITIALIZER;
std::atomic<bool> server_running(true);

// Round Robin
struct RoundRobinRequest
{
    int client_socket;
    int offset;
    int client_id;
};
std::queue<int> round_robin_queue;
pthread_mutex_t round_robin_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t round_robin_cond = PTHREAD_COND_INITIALIZER;
std::atomic<bool> round_robin_server_running(true);

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

void process_request_fifo(const FifoRequest &req)
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

void *fcfs_scheduler(void *arg)
{
    while (server_running)
    {
        pthread_mutex_lock(&queue_mutex);
        while (request_queue.empty() && server_running)
        {
            pthread_cond_wait(&queue_cond, &queue_mutex);
        }
        if (!server_running && request_queue.empty())
        {
            pthread_mutex_unlock(&queue_mutex);
            break;
        }
        FifoRequest req = request_queue.front();
        request_queue.pop();
        std ::cout << "Processing request from client " << req.client_socket << " at offset " << req.offset << std::endl;
        pthread_mutex_unlock(&queue_mutex);

        process_request_fifo(req);
    }
    return NULL;
}

void *rr_scheduler(void *arg)
{
}

void *handle_client_fifo(void *arg)
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

        FifoRequest req{client_socket, offset};
        pthread_mutex_lock(&queue_mutex);
        request_queue.push(req);
        pthread_cond_signal(&queue_cond);
        pthread_mutex_unlock(&queue_mutex);
    }

    close(client_socket);
    return NULL;
}

void *handle_client_rr(void *arg)
{
}

void use_fifo_schedule(int server_socket_fd, sockaddr_in address, int address_len)
{
    pthread_t scheduler_thread;                  // Thread for the scheduler
    std::vector<pthread_t> threads(num_clients); // Vector to store the thread IDs for the clients

    pthread_create(&scheduler_thread, NULL, fcfs_scheduler, NULL); // Create the scheduler thread
    for (int i = 0; i < num_clients; i++)                          // Loop to accept multiple clients
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

        int rc = pthread_create(&threads[i], NULL, handle_client_fifo, (void *)data);
        if (rc)
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
    pthread_cond_signal(&queue_cond);
    pthread_join(scheduler_thread, NULL);
    return;
}

void use_rr_schedule(int server_socket_fd, sockaddr_in address, int address_len)
{
}

// Concurrent
void handle_clients(int server_socket_fd, sockaddr_in address, int address_len)
{
    if (policy == 0)
    {
        std ::cout << "Using FIFO scheduling" << std::endl;
        use_fifo_schedule(server_socket_fd, address, address_len);
    }
    else if (policy == 1)
    {
        std ::cout << "Using RR scheduling" << std::endl;
        use_rr_schedule(server_socket_fd, address, address_len);
    }
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
    read_config(); // Reading configuration
    read_words();  // Loading the words from the file
    server();      // Initiazling the server and start handling client requests

    // Check the scheduling policy
    if (argv[0] == "fifo")
    {
        policy = 0;
    }
    else if (argv[0] == "rr")
    {
        policy = 1;
    }
    else if (argv[0] == "fair")
    {
        policy = 2;
    }
}