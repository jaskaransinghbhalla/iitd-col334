#include "client_util.h"
#include "json.hpp"
#include <algorithm>
#include <arpa/inet.h>
#include <chrono>
#include <cstring>
#include <fstream>
#include <iostream>
#include <netdb.h>
#include <random>
#include <sstream>
#include <sys/socket.h>
#include <unistd.h>

const int BUFFER_SIZE = 1024;
const int MAX_ATTEMPTS = 10;

std::string output_file = "output";

// General utility functions

int connect_to_server()
{
  int client_sock_fd = socket(AF_INET, SOCK_STREAM, 0);
  if (client_sock_fd == -1)
  {
    perror("Socket creation failed");
    exit(EXIT_FAILURE);
  }

  sockaddr_in address;
  address.sin_family = AF_INET;
  address.sin_port = htons(port);

  if (ip_address == "0.0.0.0" || ip_address == "INADDR_ANY")
  {
    address.sin_addr.s_addr = INADDR_ANY;
  }
  else
  {
    if (inet_pton(AF_INET, ip_address.c_str(), &address.sin_addr) <= 0)
    {
      std::cerr << "Invalid address/ Address not supported" << std::endl;
      exit(EXIT_FAILURE);
    }
  }

  if (connect(client_sock_fd, (struct sockaddr *)&address, sizeof(address)) <
      0)
  {
    perror("Connection failed");
    exit(EXIT_FAILURE);
  }

  std::cout << "Connected to server: " << ip_address << ":" << port
            << std::endl;
  return client_sock_fd;
}

void count_word(const std::string &word,
                std::map<std::string, int> &wordFrequency)
{
  std::string s = "";
  s += EOF;
  if (word != "\n" && word != s)
  {
    wordFrequency[word]++;
  }
}

std::string get_last_word(const std::string &packet_data)
{
  std::istringstream iss(packet_data);
  std::string word, last_word;

  while (iss >> word)
  {
    last_word = word;
  }

  return last_word;
}

void process_packet(const std::string &packet_data,
                    std::map<std::string, int> &wordFrequency)
{
  std::vector<std::string> words;
  std::istringstream iss(packet_data);
  std::string word;

  while (std::getline(iss, word, ','))
  {
    word.erase(0, word.find_first_not_of(" \t\n\r\f\v"));
    word.erase(word.find_last_not_of(" \t\n\r\f\v") + 1);
    if (!word.empty())
    {
      words.push_back(word);
    }
  }

  for (const auto &w : words)
  {
    count_word(w, wordFrequency);
  }
  return;

  // return words.empty() ? "" : words.back();
}

void write_with_of_stream(const std::string &filename,
                          const std::string &content, bool append = false)
{
  std::ofstream outFile;
  if (append)
  {
    outFile.open(filename, std::ios_base::app);
  }
  else
  {
    outFile.open(filename);
  }

  if (outFile.is_open())
  {
    outFile << content;
    outFile.close();
  }
}

void print_word_freq(const ClientInfo *client_info)
{
  std::string client_output_file =
      output_file + "_" + std::to_string(client_info->client_id) + ".txt";
  write_with_of_stream(client_output_file, "", false);

  std::vector<std::pair<std::string, int>> pairs;
  for (const auto &item : client_info->wordFrequency)
  {
    pairs.push_back(item);
  }

  std::sort(pairs.begin(), pairs.end());

  for (const auto &pair : pairs)
  {
    std::string result = pair.first + "," + std::to_string(pair.second) + '\n';
    write_with_of_stream(client_output_file, result, true);
  }
}

// Utility functions for Protocols
int generate_random_integer(int x, int y)
{
  std::random_device rd; // Initialize a random device
  std::mt19937 gen(
      rd()); // Use a Mersenne Twister engine to generate random numbers
  std::uniform_int_distribution<> dis(
      x, y);       // Create a distribution for numbers in the range [1, x]
  return dis(gen); // Generate and return the random number
}

bool should_send_request(ClientInfo *client_info)
{
  auto current_time = std::chrono::duration_cast<std::chrono::milliseconds>(
                          std::chrono::system_clock::now().time_since_epoch())
                          .count();
  if (current_time % client_info->time_slot_len == 0)
  {
    int random_integer = generate_random_integer(1, client_info->num_clients);
    if (random_integer == 1 &&
        current_time != client_info->latest_request_sent_timestamp)
    {
      client_info->latest_request_sent_timestamp = current_time;
      return true;
    }
  }
  return false;
}

// Slotted Aloha
void request_words_slotted_aloha(int client_sock_fd, ClientInfo *client_info)
{
  char buffer[BUFFER_SIZE] = {0};
  bool eof = false;

  while (true)
  {
    // Request
    std::string req_payload = std::to_string(client_info->offset) + "\n";

    if (should_send_request(client_info)) // Should send request
    {
      if (send(client_sock_fd, req_payload.c_str(), req_payload.length(), 0) <
          -1)
      {
        perror("Client request failed");
        exit(EXIT_FAILURE);
      }

      if (strcmp(buffer, "$$\n") == 0)
      {
        break;
      }

      int word_count = 0;
      std::string accumulated_data;
      std::vector<std::string> packets_to_process;

      while (word_count < num_word_per_request)
      {
        char buffer_temp[2] = {0};
        int valread = recv(client_sock_fd, buffer_temp, 1, 0);

        if (valread < 0)
        {
          perror("Error reading from server");
          exit(EXIT_FAILURE);
        }

        if (*buffer_temp == '\n')
        {
          if (accumulated_data == "HUH!")
          {
            std::cout << client_sock_fd
                      << " : Server busy, Dropping the following Packets"
                      << std::endl;
            accumulated_data = "";
            packets_to_process.clear();
            continue;
          }

          packets_to_process.push_back(accumulated_data);
          std::string last_word = get_last_word(accumulated_data);

          std::string s = "";
          s += EOF;

          if (last_word == s)
          {
            for (const auto &packet : packets_to_process)
            {
              process_packet(packet, client_info->wordFrequency);
            }
            eof = true;
            break;
          }
          for (const auto &packet : packets_to_process)
          {
            process_packet(packet, client_info->wordFrequency);
          }
          word_count += words_per_packet;
          accumulated_data = "";
          packets_to_process.clear();
        }
        else
        {
          accumulated_data += buffer_temp[0];
        }
      }

      if (!eof)
      {
        client_info->offset += num_word_per_request;
      }
      else
      {
        break;
      }
    }
  }

  close(client_sock_fd);
}

void beb(int attempts, int time_slot_len)
{
  if (attempts > MAX_ATTEMPTS)
  {
    std::cerr << "Max attempts reached, exiting" << std::endl;
    exit(EXIT_FAILURE);
  }

  int backoff_time = time_slot_len * generate_random_integer(0, ((int)pow(2, attempts) - 1)); // Generate random backoff time
  std::cout << "Backoff time: " << backoff_time << "ms" << std::endl;
  // std::this_thread::sleep_for(std::chrono::milliseconds(backoff_time));
  sleep(backoff_time / 1000);
}
// Binary Exponential Backoff
void request_words_binary_exponential_backoff(int client_sock_fd, ClientInfo *client_info)
{
  char buffer[BUFFER_SIZE] = {0};
  bool eof = false;
  int attempts = 0;

  while (true)
  {
    // Request
    std::string req_payload = std::to_string(client_info->offset) + "\n";

    if (send(client_sock_fd, req_payload.c_str(), req_payload.length(), 0) <
        -1)
    {
      perror("Client request failed");
      exit(EXIT_FAILURE);
    }

    if (strcmp(buffer, "$$\n") == 0)
    {
      break;
    }

    int word_count = 0;
    std::string accumulated_data;
    std::vector<std::string> packets_to_process;

    while (word_count < num_word_per_request)
    {
      char buffer_temp[2] = {0};
      int valread = recv(client_sock_fd, buffer_temp, 1, 0);

      if (valread < 0)
      {
        perror("Error reading from server");
        exit(EXIT_FAILURE);
      }

      if (*buffer_temp == '\n')
      {
        if (accumulated_data == "HUH!")
        {
          std::cout << client_sock_fd << " : Server busy, initating backoff"
                    << std::endl;

          accumulated_data = "";
          packets_to_process.clear();

          attempts++;
          beb(attempts, client_info->time_slot_len);
          continue;
        }

        packets_to_process.push_back(accumulated_data);
        std::string last_word = get_last_word(accumulated_data);

        std::string s = "";
        s += EOF;

        if (last_word == s)
        {
          for (const auto &packet : packets_to_process)
          {
            process_packet(packet, client_info->wordFrequency);
          }
          eof = true;
          attempts = 0;
          break;
        }
        for (const auto &packet : packets_to_process)
        {
          process_packet(packet, client_info->wordFrequency);
        }
        attempts = 0;
        word_count += words_per_packet;
        accumulated_data = "";
        packets_to_process.clear();
      }
      else
      {
        accumulated_data += buffer_temp[0];
      }
    }

    if (!eof)
    {
      client_info->offset += num_word_per_request;
    }
    else
    {
      break;
    }
  }
}

// Sensing and Binary Exponential Backoff
void request_words_sensing_and_beb(int client_sock_fd,ClientInfo *client_info) {
  int attempts = 0;
  char buffer[BUFFER_SIZE] = {0};
  char sense_buffer[5] = {0};

  bool eof = false;

  while (true) {
    if (send(client_sock_fd, "BUSY?\n", 6, 0) < -1) {
      perror("Client request failed");
      exit(EXIT_FAILURE);
    }

    if (strcmp(buffer, "$$\n") == 0) {
      break;
    }

    int valread = recv(client_sock_fd, sense_buffer, BUFFER_SIZE, 0);
    if (valread < 0) {
      perror("Error reading from server");
      exit(EXIT_FAILURE);
    }

    if (strcmp(sense_buffer, "BUSY\n") == 0) {
      std::cout << client_sock_fd << " : Server status is busy, waiting for " << client_info->time_slot_len << "ms" << std::endl;
      // beb(1, client_info->time_slot_len);
      sleep(client_info->time_slot_len / 1000);
      continue;
    } else if (strcmp(sense_buffer, "IDLE\n") == 0) {
      std::cout << client_sock_fd << " : Server status is idle, sending request" << std::endl;
      std::string req_payload = std::to_string(client_info->offset) + "\n";

      if (send(client_sock_fd, req_payload.c_str(), req_payload.length(), 0) <
          -1) {
        perror("Client request failed");
        exit(EXIT_FAILURE);
      }

      if (strcmp(buffer, "$$\n") == 0) {
        break;
      }

      int word_count = 0;
      std::string accumulated_data;
      std::vector<std::string> packets_to_process;

      while (word_count < num_word_per_request) {
        char buffer_temp[2] = {0};
        int valread = recv(client_sock_fd, buffer_temp, 1, 0);

        if (valread < 0) {
          perror("Error reading from server");
          exit(EXIT_FAILURE);
        }

        if (*buffer_temp == '\n') {
          if (accumulated_data == "HUH!") {
            std::cout << client_sock_fd
                      << " : Server busy, Dropping the following Packets"
                      << std::endl;
            accumulated_data = "";
            packets_to_process.clear();
            beb(attempts, client_info->time_slot_len);
            continue;
          }

          packets_to_process.push_back(accumulated_data);
          std::string last_word = get_last_word(accumulated_data);

          std::string s = "";
          s += EOF;

          if (last_word == s) {
            for (const auto &packet : packets_to_process) {
              process_packet(packet, client_info->wordFrequency);
            }
            eof = true;
            break;
          }
          for (const auto &packet : packets_to_process) {
            process_packet(packet, client_info->wordFrequency);
          }
          attempts = 0;
          word_count += words_per_packet;
          accumulated_data = "";
          packets_to_process.clear();
        } else {
          accumulated_data += buffer_temp[0];
        }
      }

      if (!eof) {
        client_info->offset += num_word_per_request;
      } else {
        break;
      }
    } else {
      // got something invalid from the server, panic and exit
      std::cerr << "Invalid response from server, exiting" << std::endl;}
  }
}

// Client thread functions
void *client_thread_slotted_aloha(void *arg) // Client thread function
{
  ClientInfo *client_info =
      static_cast<ClientInfo *>(arg);                       // Cast argument to ClientInfo pointer
  int client_sock_fd = connect_to_server();                 // Connect to server
  request_words_slotted_aloha(client_sock_fd, client_info); // Request words from server
  print_word_freq(client_info);                             // Print word frequency
  pthread_exit(nullptr);                                    // Exit thread
}

void *
client_thread_binary_exponential_backoff(void *arg) // Client thread function
{
  ClientInfo *client_info =
      static_cast<ClientInfo *>(arg);       // Cast argument to ClientInfo pointer
  int client_sock_fd = connect_to_server(); // Connect to server
  request_words_binary_exponential_backoff(
      client_sock_fd, client_info); // Request words from server
  print_word_freq(client_info);     // Print word frequency
  pthread_exit(nullptr);            // Exit thread
}

void *client_thread_sensing_and_beb(void *arg) // Client thread function
{
  ClientInfo *client_info =
      static_cast<ClientInfo *>(arg);       // Cast argument to ClientInfo pointer
  int client_sock_fd = connect_to_server(); // Connect to server
  request_words_sensing_and_beb(client_sock_fd,
                                client_info); // Request words from server
  print_word_freq(client_info);               // Print word frequency
  pthread_exit(nullptr);                      // Exit thread
}