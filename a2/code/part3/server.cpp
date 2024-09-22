// Server

// Packages
#include "json.hpp"
#include <arpa/inet.h> // Provides functions for manipulating IP addresses (like inet_addr)
#include <chrono>
#include <fstream>      // Provides file stream classes for reading/writing files
#include <iostream>     // Provides input/output stream objects like cin, cout, cerr
#include <netdb.h>      // Provides functions for network address and service translation
#include <netinet/in.h> // Provides Internet address family structures and constants
#include <pthread.h>    // Provides functions for creating and managing threads
#include <atomic>
#include <sys/socket.h> // Includes core functions and structures for socket programming
#include <unistd.h>     // Provides access to the POSIX operating system API

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
std::atomic<bool> collision_detected(false);

// Server Status
enum SERVER_STATUS
{
  IDLE = 0,
  BUSY = 1
};

struct server_info
{
  SERVER_STATUS status = IDLE;
  int client_socket = -1;
  int start_time = 0;
  int last_concurrent_request_time = 0;
};

struct server_info server_info;

pthread_mutex_t server_info_status_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t server_info_lcrt_mutex = PTHREAD_MUTEX_INITIALIZER;

// Client Info
struct thread_data
{
  int client_socket;
};

///////////////////////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////// Utility functions //////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////

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

// Get time in milliseconds since epoch
long long get_time_in_milliseconds()
{
  return std::chrono::duration_cast<std::chrono::milliseconds>(
             std::chrono::high_resolution_clock::now().time_since_epoch())
      .count();
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

bool handle_client_request(int client_socket) // Basil
{
  pthread_mutex_lock(&server_info_status_mutex);
  if (server_info.last_concurrent_request_time > server_info.start_time)
  {
    // Collision detected, stop processing
    collision_detected = true;
    pthread_mutex_unlock(&server_info_status_mutex);
    return false;
  }
  pthread_mutex_unlock(&server_info_status_mutex);

  char buffer[BUFFER_SIZE] = {0};

  memset(buffer, 0, BUFFER_SIZE); // Clear the buffer

  fd_set read_fds;
  struct timeval timeout;

  // Initialize the file descriptor set
  FD_ZERO(&read_fds);
  FD_SET(client_socket, &read_fds);

  // Set timeout to 5 seconds
  timeout.tv_sec = 5;
  timeout.tv_usec = 0;

  // Wait for the socket to be ready for reading
  int select_result = select(client_socket + 1, &read_fds, NULL, NULL, &timeout);

  if (select_result > 0 && FD_ISSET(client_socket, &read_fds))
  {
    int valread = read(client_socket, buffer, BUFFER_SIZE);
    if (valread <= 0)
      return false;
  }
  else if (select_result == 0)
  {
    // Timeout occurred
    std::cout << client_socket << " : Timeout" << std::endl;
    return false;
  }
  else
  {
    // Error occurred
    perror("select error");
    return false;
  }

  int offset = std::stoi(buffer);
  std::cout << client_socket << " : Requested offset: " << offset << std::endl;

  if (offset >= words.size())
  {
    // If the offset is too large, sends "$$\n" to the client, indicating an
    // invalid offset
    if (send(client_socket, "$$\n", 3, 0) < -1)
    {
      perror("Could not send packet");
      exit(EXIT_FAILURE);
    }
    return true;
  }

  // Valid offset
  bool eof = false;

  for (int word_count = 0; word_count < num_word_per_request && !eof && !collision_detected;) // Loop to send the requested words to the client
  {

    std::string packet; // Packet to be sent to the client

    for (int packet_count = 0; packet_count < words_per_packet && word_count < num_word_per_request && !eof && !collision_detected; packet_count++, word_count++)
    {
      std::string word = words[offset + word_count];
      packet += word;
      packet += ",";

      std::string s = "";
      s += EOF;
      if (word == s)
      {
        eof = true;
        break;
      }
    }

    packet.pop_back();      // Remove the last comma
    packet = packet + "\n"; // Add a newline character at the end of the packet

    if (send(client_socket, packet.c_str(), packet.length(), 0) < -1)
    {
      perror("Could not send packet");
      exit(EXIT_FAILURE);
    } // Send the packet to the client
  }
  std::cout << "" << client_socket << " : Request handled" << std::endl;
  return true;
}

bool check_control_req(int client_socket)
{
  char temp_buffer[6] = {0};
  memset(temp_buffer, 0, 6); // Clear the buffer

  int r = recv(client_socket, temp_buffer, 6, MSG_PEEK | MSG_DONTWAIT);
  while (r < -1 && errno == EAGAIN && errno == EWOULDBLOCK && client_socket != -1)
  {
    fd_set read_fds;
    struct timeval timeout;

    // Initialize the file descriptor set
    FD_ZERO(&read_fds);
    FD_SET(client_socket, &read_fds);

    // Set timeout to 5 seconds
    timeout.tv_sec = 5;
    timeout.tv_usec = 0;

    // Wait for the socket to be ready for reading
    int select_result = select(client_socket + 1, &read_fds, NULL, NULL, &timeout);

    if (select_result > 0 && FD_ISSET(client_socket, &read_fds))
    {
      r = recv(client_socket, temp_buffer, 6, MSG_PEEK | MSG_DONTWAIT);
    }
    else if (select_result == 0)
    {
      // Timeout occurred
      std::cerr << "Timeout occurred while waiting for control request" << std::endl;
      return false;
    }
    else
    {
      // Error occurred
      perror("select error");
      return false;
    }
  }

  if (r == 6 && strcmp(temp_buffer, "BUSY?\n") == 0)
  {
    memset(temp_buffer, 0, 6); // Clear the buffer
    read(client_socket, temp_buffer, 6);
    return true;
  }

  return false;
}

void handle_client_requests(int client_socket)
{
  int total_words_sent = 0;
  bool is_collision = false;

  while (total_words_sent < words.size())
  {
    bool is_control_request = check_control_req(client_socket);

    if (pthread_mutex_trylock(&server_info_status_mutex) == 0) // Try to acquire the lock
    {
      // Successfully acquired the lock
      if (server_info.status == IDLE)
      {
        // Server is idle, we can process this request
        if (is_control_request)
        {
          send(client_socket, "IDLE\n", 5, 0);
          pthread_mutex_unlock(&server_info_status_mutex);
          continue;
        }
        server_info.status = BUSY;
        server_info.client_socket = client_socket;
        server_info.start_time = get_time_in_milliseconds();
        is_collision = false;
        collision_detected = false;
        pthread_mutex_unlock(&server_info_status_mutex);

        // Handle the client request

        bool s = handle_client_request(client_socket);
        if (!s)
        {
          server_info.status = IDLE;
          server_info.client_socket = -1;
          server_info.start_time = 0;
          collision_detected = false;
          continue;
        }

        // Check if a collision occurred during handling
        if (collision_detected)
        {
          is_collision = true;
        }
        else
        {
          // Reset server status after successful handling
          total_words_sent += num_word_per_request;
          pthread_mutex_lock(&server_info_status_mutex);
          server_info.status = IDLE;
          server_info.client_socket = -1;
          server_info.start_time = 0;
          collision_detected = false;
          is_collision = false;
          pthread_mutex_unlock(&server_info_status_mutex);
        }
      }
      else
      {
        // Server is busy, this is a collision
        is_collision = true;
        pthread_mutex_unlock(&server_info_status_mutex);
      }
    }
    else
    {
      // Couldn't acquire the lock, this is also a collision
      is_collision = true;
    }

    if (is_collision)
    {
      if (is_control_request)
      {
        send(client_socket, "BUSY\n", 5, 0);
        continue;
      }
      // Handle collision
      pthread_mutex_lock(&server_info_lcrt_mutex);
      long long current_time = get_time_in_milliseconds();
      server_info.last_concurrent_request_time = current_time;
      pthread_mutex_unlock(&server_info_lcrt_mutex);

      // Set the collision flag to stop any ongoing client handling
      collision_detected = true;

      // Send "HUH!" to the client that caused the collision
      send(client_socket, "HUH!\n", 5, 0);

      // Send "HUH!" to the client being served (if there is one)
      pthread_mutex_lock(&server_info_status_mutex);
      if (server_info.status == BUSY && server_info.client_socket != -1 && server_info.client_socket != client_socket)
      {
        send(server_info.client_socket, "HUH!\n", 5, 0);
      }
      // Reset server status
      server_info.status = IDLE;
      server_info.client_socket = -1;
      server_info.start_time = 0;
      collision_detected = false;
      is_collision = false;
      pthread_mutex_unlock(&server_info_status_mutex);
    }
  }
}

void *handle_client_thread(void *arg)
{
  struct thread_data *data = (struct thread_data *)arg;
  int client_socket = data->client_socket;
  std::cout << "" << client_socket << " : Thread started" << std::endl;
  handle_client_requests(client_socket);
  std::cout << "" << client_socket << " : Thread finished" << std::endl;
  close(client_socket);
  delete data;
  pthread_exit(NULL);
}

void handle_clients(int server_socket_fd, sockaddr_in address, int address_len)
{
  std::vector<pthread_t> threads(num_clients); // Vector to store the thread IDs
  for (int i = 0; i < num_clients; i++)        // Loop to accept multiple clients
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
    int rc = pthread_create(&threads[i], NULL, handle_client_thread, (void *)data);
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
  std::cout << "All clients have finished." << std::endl;
  return;
}

void server()
{

  // Sever Socket

  // In Unix-like systems, sockets are treated as files, and each is assigned
  // a unique file descriptor (which is just an integer).
  // - AF_INET: Indicates that the socket will use the IPv4 protocol.
  // - SOCK_STREAM: Specifies the type of socket. This type provides
  // connection-oriented, reliable, and order-preserving data transmission.
  // - 0: This parameter specifies the protocol to be used, and TCP (the
  // default protocol) is selected.
  int server_socket_fd = socket(AF_INET, SOCK_STREAM, 0);

  // Check if the socket was created successfully or not, if it is not created
  // it should return -1
  if (server_socket_fd == -1)
  {
    perror("socket creation failure");
    exit(EXIT_FAILURE);
  }

  // Server Address

  // sockaddr_in is a structure used to represent an Internet Protocol version
  // 4(IPv4)socket address.
  // - sin_family: This member specifies the address family. AF_INET is used
  // for IPv4.
  // - sin_port: Specifies the port number as a 16-bit integer.
  // - sin_addr.s_addr: This member holds the IP address.
  sockaddr_in address;
  int address_len = sizeof(address);
  address.sin_family = AF_INET;
  if (ip_address == "0.0.0.0" || ip_address == "INADDR_ANY")
  {
    // std::cout << ip_address;
    // If the config specifies 0.0.0.0 or INADDR_ANY, use INADDR_ANY
    address.sin_addr.s_addr = INADDR_ANY;
  }
  else
  {
    // Otherwise, use the IP address from the config file
    if (inet_pton(AF_INET, ip_address.c_str(), &address.sin_addr) <= 0)
    {
      std::cerr << "Invalid address/ Address not supported" << std::endl;
    }
  }

  address.sin_port = htons(port);

  // Binding

  // The part where we bind the socket to an IP address and a port
  // Binding a socket means associating the socket with a specific address and
  // port number on the local machine. It tells the operating system that you
  // want to receive incoming connections on a specific IP address and port
  // combination Note: If you don't bind a socket explicitly, the system will
  // assign a random port when you start listening or connecting.
  if (bind(server_socket_fd, reinterpret_cast<sockaddr *>(&address),
           address_len) < 0)
  {
    perror("bind failed");
    exit(EXIT_FAILURE);
  }

  // Listening

  // Listening on a socket means configuring the socket to accept incoming
  // connection requests. It prepares the socket to receive client
  // connections, creating a queue for incoming connection requests. SOMACONN
  // You specify a backlog parameter, which defines the maximum length of the
  // queue for pending connections
  if (listen(server_socket_fd, SOMAXCONN) < 0)
  {
    perror("listen failed");
    exit(EXIT_FAILURE);
  }
  std::cout << "Server listening on " << ip_address << ":" << port << std::endl;

  // hanlde clients
  handle_clients(server_socket_fd, address, address_len);
  std::cout << "Server finished" << std::endl;
  close(server_socket_fd);
  return;
}

int main()

{
  read_config(); // Reading configuration
  read_words();  // Loading the words from the file
  server();      // Initiazling the server and start handling client requests
}