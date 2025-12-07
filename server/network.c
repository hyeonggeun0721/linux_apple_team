#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include "network.h"

int server_fd;
int client_fds[2] = {0, 0};

void init_server() {
    struct sockaddr_in server_addr;
    int opt = 1;
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == -1) exit(EXIT_FAILURE);
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(PORT);
    if (bind(server_fd, (struct sockaddr *)&server_addr, sizeof(server_addr)) == -1) exit(EXIT_FAILURE);
    if (listen(server_fd, 2) == -1) exit(EXIT_FAILURE);
    printf("Server listening on port %d...\n", PORT);
}

/*void wait_for_players() {
    struct sockaddr_in client_addr;
    socklen_t addr_len = sizeof(client_addr);
    printf("Waiting for players...\n");
    for (int i = 0; i < 2; i++) {
        if ((client_fds[i] = accept(server_fd, (struct sockaddr *)&client_addr, &addr_len)) < 0) exit(EXIT_FAILURE);
        printf("Player %d connected!\n", i + 1);
        char msg[50];
        sprintf(msg, "START %d\n", i);
        write(client_fds[i], msg, strlen(msg));
    }
    printf("Both connected!\n");
}*/

void broadcast(char *msg) {
    for (int i = 0; i < 2; i++) if (client_fds[i] > 0) write(client_fds[i], msg, strlen(msg));
}

void send_message(int client_idx, char *msg) {
    if (client_fds[client_idx] > 0) write(client_fds[client_idx], msg, strlen(msg));
}

void close_server() {
    close(client_fds[0]);
    close(client_fds[1]);
    close(server_fd);
}
