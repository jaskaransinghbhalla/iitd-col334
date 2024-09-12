# Compiler
CXX = g++

# Compiler flags
CXXFLAGS = -Wall -std=c++11

# Linker flags
LDFLAGS = -lpthread

# Source files
SERVER_SRC = server.cpp
CLIENT_SRC = client.cpp client_util.cpp

# Output executables
SERVER_OUT = server
CLIENT_OUT = client

# Object files for multi-client program
CLIENT_OBJ = $(CLIENT_SRC:.cpp=.o)

# Default target
all: $(SERVER_OUT) $(CLIENT_OUT)

# Server target
$(SERVER_OUT): $(SERVER_SRC)
	$(CXX) $(CXXFLAGS) -o $@ $<


# Multi-client target
$(CLIENT_OUT): $(CLIENT_OBJ)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

# Rule for object files
%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Clean target
clean:
	rm -f $(SERVER_OUT) $(CLIENT_OUT) *.o

# Run target for server and single client
run: $(SERVER_OUT) $(CLIENT_OUT)
	./$(SERVER_OUT) & ./$(CLIENT_OUT)

# Phony targets
.PHONY: all clean run run_multi