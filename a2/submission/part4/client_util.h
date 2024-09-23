#ifndef CLIENT_UTIL_H
#define CLIENT_UTIL_H

#include <string>
#include <map>
#include <atomic>

// Structure to hold client information
struct ClientInfo
{
    bool eof = false;
    int client_id;
    int num_word_per_request;
    int offset;
    int port;
    int words_per_packet;
    pthread_mutex_t client_mutex;
    std::atomic<bool> is_done{false};
    bool is_processing{false};
    std::map<std::string, int> wordFrequency;
    std::string ip_address;
};

// Function prototypes
int connect_to_server();
void request_words(int client_sock_fd, ClientInfo *client_info);
void print_word_freq(const ClientInfo *client_info);
void *client_thread(void *arg);
void *client_thread_rogue(void *arg);

// Global variables (consider making these non-global in a real application)
extern int num_clients;
extern int num_word_per_request;
extern int port;
extern int words_per_packet;
extern std::string ip_address;
extern std::string output_file;

#endif // CLIENT_H