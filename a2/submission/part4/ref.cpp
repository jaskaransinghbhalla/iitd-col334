#include <pthread.h>
#include <queue>
#include <cstring>
#include <atomic>

// ... (previous includes and global variables remain the same)

struct Request {
    int client_socket;
    int offset;
};

std::queue<Request> request_queue;
pthread_mutex_t queue_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t queue_cond = PTHREAD_COND_INITIALIZER;
std::atomic<bool> server_running(true);

void process_request(const Request& req) {
    int client_socket = req.client_socket;
    int offset = req.offset;

    // Invalid Offset
    if (offset >= words.size()) {
        send(client_socket, "$$\n", 3, 0);
        return;
    }

    // Valid offset
    bool eof = false;
    for (int word_count = 0; word_count < num_word_per_request && !eof;) {
        std::string packet;
        for (int packet_count = 0; packet_count < words_per_packet && word_count < num_word_per_request && !eof; packet_count++, word_count++) {
            std::string word = words[offset + word_count];
            packet += word + ",";

            if (word.length() == 1 && word[0] == EOF) {
                eof = true;
                break;
            }
        }
        if (!packet.empty()) {
            packet.pop_back(); // Remove the last comma
            packet += "\n";
            send(client_socket, packet.c_str(), packet.length(), 0);
        }
    }
}

void* fcfs_scheduler(void* arg) {
    while (server_running) {
        pthread_mutex_lock(&queue_mutex);
        while (request_queue.empty() && server_running) {
            pthread_cond_wait(&queue_cond, &queue_mutex);
        }
        if (!server_running && request_queue.empty()) {
            pthread_mutex_unlock(&queue_mutex);
            break;
        }
        Request req = request_queue.front();
        request_queue.pop();
        pthread_mutex_unlock(&queue_mutex);
        process_request(req);
    }
    return NULL;
}

void* handle_client(void* arg) {
    int client_socket = *((int*)arg);
    delete (int*)arg;

    char buffer[BUFFER_SIZE] = {0};
    while (true) {
        memset(buffer, 0, BUFFER_SIZE);
        int valread = read(client_socket, buffer, BUFFER_SIZE);
        if (valread <= 0)
            break;

        int offset = std::stoi(buffer);
        
        Request req{client_socket, offset};
        pthread_mutex_lock(&queue_mutex);
        request_queue.push(req);
        pthread_cond_signal(&queue_cond);
        pthread_mutex_unlock(&queue_mutex);
    }

    close(client_socket);
    return NULL;
}

void handle_clients(int server_socket_fd, sockaddr_in address, int address_len) {
    pthread_t scheduler_thread;
    pthread_create(&scheduler_thread, NULL, fcfs_scheduler, NULL);

    pthread_t client_threads[num_clients];

    for (int i = 0; i < num_clients; i++) {
        int* client_socket = new int;
        *client_socket = accept(server_socket_fd, reinterpret_cast<sockaddr*>(&address), reinterpret_cast<socklen_t*>(&address_len));
        if (*client_socket < 0) {
            perror("accept failed");
            delete client_socket;
            continue;
        }

        if (pthread_create(&client_threads[i], NULL, handle_client, (void*)client_socket) != 0) {
            perror("pthread_create failed");
            delete client_socket;
            close(*client_socket);
        }
    }

    for (int i = 0; i < num_clients; i++) {
        pthread_join(client_threads[i], NULL);
    }

    server_running = false;
    pthread_cond_signal(&queue_cond);
    pthread_join(scheduler_thread, NULL);
}

void server() {
    // ... (your existing server setup code)

    handle_clients(server_socket_fd, address, address_len);
    close(server_socket_fd);
}

int main() {
    read_config();
    read_words();
    server();

    pthread_mutex_destroy(&queue_mutex);
    pthread_cond_destroy(&queue_cond);
    return 0;
}