#ifndef CLIENT_UTIL_H
#define CLIENT_UTIL_H

#include <string>
#include <map>

// Structure to hold client information
struct ClientInfo
{
    // Unique to client
    int client_id;
    int offset;
    std::map<std::string, int> wordFrequency;
    // Shared among clients
    int num_word_per_request;
    int port;
    int words_per_packet;
    std::string ip_address;
    int time_slot_len;
    int num_clients;
    long long latest_request_sent_timestamp;
};

// Function prototypes
int connect_to_server();
void request_words(int client_sock_fd, ClientInfo *client_info);
void print_word_freq(const ClientInfo *client_info);
void *client_thread(void *arg);

// Global variables (consider making these non-global in a real application)
extern int num_clients;
extern int num_word_per_request;
extern int port;
extern int words_per_packet;
extern std::string ip_address;
extern std::string output_file;

#endif // CLIENT_H