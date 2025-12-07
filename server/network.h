#ifndef NETWORK_H
#define NETWORK_H
#include <netinet/in.h>
#define PORT 8080
#define BUFFER_SIZE 1024
extern int server_fd;
extern int client_fds[2];
void init_server();
void wait_for_players();
void broadcast(char *msg);
void send_message(int client_idx, char *msg);
void close_server();
#endif
