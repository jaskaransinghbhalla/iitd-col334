# Compiler
CXX = g++

# Compiler flags
CXXFLAGS = -Wall -std=c++11

# Source files
SERVER_SRC = server.cpp
CLIENT_SRC = client.cpp

# Output executables
SERVER_OUT = server
CLIENT_OUT = client

# Default target
all: $(SERVER_OUT) $(CLIENT_OUT)

# Server target
$(SERVER_OUT): $(SERVER_SRC)
	$(CXX) $(CXXFLAGS) -o $@ $<

# Client target
$(CLIENT_OUT): $(CLIENT_SRC)
	$(CXX) $(CXXFLAGS) -o $@ $<

# Clean target
clean:
	rm -f $(SERVER_OUT) $(CLIENT_OUT)

# Phony targets
.PHONY: all clean