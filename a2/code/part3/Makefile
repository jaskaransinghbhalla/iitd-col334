# Compiler
CXX = g++

# Compiler flags
CXXFLAGS = -Wall -std=c++11

# Linker flags
LDFLAGS = -lpthread

# Source files
SERVER_SRC = server.cpp
CLIENT_SRC = client_util.cpp client.cpp

# Output executables
SERVER_OUT = server
CLIENT_OUT = client

# Object files
SERVER_OBJ = $(SERVER_SRC:.cpp=.o)
CLIENT_OBJ = $(CLIENT_SRC:.cpp=.o)

# Build target
build: $(SERVER_OUT) $(CLIENT_OUT)

# Server target
$(SERVER_OUT): $(SERVER_OBJ)
	$(CXX) $(CXXFLAGS) -o $@ $^

# Client target
$(CLIENT_OUT): $(CLIENT_OBJ)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

# Run target for server and single client
run: $(SERVER_OUT) $(CLIENT_OUT)
	./$(SERVER_OUT) & ./$(CLIENT_OUT)

run-aloha: $(SERVER_OUT) $(CLIENT_OUT)
	./$(SERVER_OUT) & ./$(CLIENT_OUT) 0

run-beb: $(SERVER_OUT) $(CLIENT_OUT)
	./$(SERVER_OUT) & ./$(CLIENT_OUT) 1

run-csma: $(SERVER_OUT) $(CLIENT_OUT)
	./$(SERVER_OUT) & ./$(CLIENT_OUT) 2

# Plot target
plot: plot.py
	python3 $<

# Clean target
clean:
	rm -f $(SERVER_OUT) $(CLIENT_OUT) *.o output*.txt plot.png

# Phony targets
.PHONY: all clean run plot