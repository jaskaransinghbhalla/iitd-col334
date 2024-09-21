# Compiler
CXX = g++

# Compiler flags
CXXFLAGS = -Wall -std=c++11 -g

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
run-fifo: $(SERVER_OUT) $(CLIENT_OUT)
	./$(SERVER_OUT) fifo & ./$(CLIENT_OUT)
run-rr: $(SERVER_OUT) $(CLIENT_OUT)
	./$(SERVER_OUT) rr & ./$(CLIENT_OUT)
run-fairness : $(SERVER_OUT) $(CLIENT_OUT)
	./$(SERVER_OUT) fairness & ./$(CLIENT_OUT)

# Plot target
plot: plot.py
	python3 $<

# Clean target
clean:
	rm -f $(SERVER_OUT) $(CLIENT_OUT) *.o output*.txt plot.png

cleanall:
	rm -f $(SERVER_OUT) $(CLIENT_OUT) *.o output*.txt
cleanout :
	rm -f *.txt plot.png

# Phony targets
.PHONY: all clean run plot