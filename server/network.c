// server/network.c

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include "network.h"

int server_fd;
// 기존 단일 세션용 변수이나, 호환성 유지를 위해 남겨둠 (main.c는 all_clients 사용)
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
    
    // 대기열 크기를 30으로 설정 (다중 접속 허용)
    if (listen(server_fd, 30) == -1) exit(EXIT_FAILURE);
    
    printf("Server listening on port %d...\n", PORT);
}

// 이 함수는 main.c가 직접 세션을 관리하므로 사용되지 않지만, 컴파일 에러 방지용 유지
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
