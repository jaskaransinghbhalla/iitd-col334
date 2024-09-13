# Compiler
CXX = g++

# Compiler flags
CXXFLAGS = -Wall -std=c++11

# Sources
SERVER_SRC = server.cpp
CLIENT_SRC = client.cpp

# Plot
PLOT_SRC = plot.py

# Output executables
SERVER_OUT = server
CLIENT_OUT = client

# Default target
build: $(SERVER_OUT) $(CLIENT_OUT)

# Server target
$(SERVER_OUT): $(SERVER_SRC)
	$(CXX) $(CXXFLAGS) -o $@ $<

# Client target
$(CLIENT_OUT): $(CLIENT_SRC)
	$(CXX) $(CXXFLAGS) -o $@ $<

# Run target
run: $(SERVER_OUT) $(CLIENT_OUT)
	./$(SERVER_OUT) & ./$(CLIENT_OUT)

# Plot target
plot: $(PLOT_SRC)
	python3 $<

# Clean target
clean:
	rm -f $(SERVER_OUT) $(CLIENT_OUT) *.o

# Phony targets
.PHONY: all clean run plot