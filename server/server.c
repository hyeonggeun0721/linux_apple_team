#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/select.h> 
#include <sys/time.h>   
#include <time.h>

#define PORT 8080
#define BUFFER_SIZE 1024
#define ROWS 10
#define COLS 17

int board[ROWS][COLS];
int scores[2] = {0, 0}; 
int client_fds[2];      
int current_turn = 0;   

void init_board() {
    srand(time(NULL));
    for(int i=0; i<ROWS; i++) {
        for(int j=0; j<COLS; j++) {
            board[i][j] = (rand() % 9) + 1;
        }
    }
}

// 사용자님의 원래 규칙(네 변 검사)이 적용된 isValid
int isValid(int r1, int c1, int r2, int c2) {
    if (r1 < 0 || r1 >= ROWS || r2 < 0 || r2 >= ROWS || 
        c1 < 0 || c1 >= COLS || c2 < 0 || c2 >= COLS) return 0;

    int sum = 0;
    int r1_has_val = 0;
    int r2_has_val = 0;
    int c1_has_val = 0;
    int c2_has_val = 0;
    int all_zero = 1;

    for (int r = r1; r <= r2; r++) {
        for (int c = c1; c <= c2; c++) {
            if (board[r][c] != 0) {
                all_zero = 0;
                sum += board[r][c];
                if (r == r1) r1_has_val = 1;
                if (r == r2) r2_has_val = 1;
                if (c == c1) c1_has_val = 1;
                if (c == c2) c2_has_val = 1;
            }
        }
    }

    if (all_zero) return 0;

    // 조건: 합이 10이고, 4개의 변 모두에 0이 아닌 숫자가 포함되어야 함
    if (sum == 10 && r1_has_val && r2_has_val && c1_has_val && c2_has_val) {
        // 정답이면 보드 지우기
        for (int r = r1; r <= r2; r++) {
            for (int c = c1; c <= c2; c++) {
                board[r][c] = 0;
            }
        }
        return 1; // 성공
    }
    
    return 0; // 실패
}

void broadcast(char *msg) {
    for (int i = 0; i < 2; i++) {
        if (client_fds[i] > 0) {
            write(client_fds[i], msg, strlen(msg));
        }
    }
}

int main() {
    setbuf(stdout, NULL);
    int server_fd;
    struct sockaddr_in server_addr, client_addr;
    socklen_t addr_len = sizeof(client_addr);
    int opt = 1;
    char buffer[BUFFER_SIZE];

    init_board();

    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == -1) exit(EXIT_FAILURE);
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(PORT);

    if (bind(server_fd, (struct sockaddr *)&server_addr, sizeof(server_addr)) == -1) {
        perror("bind"); exit(EXIT_FAILURE);
    }
    if (listen(server_fd, 2) == -1) exit(EXIT_FAILURE);

    printf("Waiting for players...\n");

    for (int i = 0; i < 2; i++) {
        if ((client_fds[i] = accept(server_fd, (struct sockaddr *)&client_addr, &addr_len)) < 0) {
            perror("accept"); exit(EXIT_FAILURE);
        }
        printf("Player %d connected! (fd: %d)\n", i + 1, client_fds[i]);
        
        char welcome_msg[50];
        sprintf(welcome_msg, "START %d\n", i);
        write(client_fds[i], welcome_msg, strlen(welcome_msg));
    }

    printf("Both players connected! Sending board data...\n");

    char board_msg[4096] = "BOARD";
    char temp[16];
    for(int i=0; i<ROWS; i++) {
        for(int j=0; j<COLS; j++) {
            sprintf(temp, " %d", board[i][j]);
            strcat(board_msg, temp);
        }
    }
    strcat(board_msg, "\n");
    broadcast(board_msg);

    printf("Game Start! Turn: Player 1\n");

    while (1) {
        int player_id = current_turn; 
        int other_id = (current_turn + 1) % 2;
        
        fd_set read_fds;
        FD_ZERO(&read_fds);
        
        FD_SET(client_fds[player_id], &read_fds);
        
        int max_fd = client_fds[player_id];

        printf("Waiting for Player %d's move (fd: %d)...\n", player_id + 1, client_fds[player_id]);

        int ready = select(max_fd + 1, &read_fds, NULL, NULL, NULL);

        if (ready < 0) {
            perror("select error");
            break;
        }

        if (FD_ISSET(client_fds[player_id], &read_fds)) {
            
            memset(buffer, 0, BUFFER_SIZE);
            int bytes_read = read(client_fds[player_id], buffer, BUFFER_SIZE);
            
            if (bytes_read <= 0) {
                printf("Player %d disconnected.\n", player_id + 1);
                break;
            }

            char cmd[10];
            int r1, c1, r2, c2;
            sscanf(buffer, "%s %d %d %d %d", cmd, &r1, &c1, &r2, &c2);

            if (strcmp(cmd, "MOVE") == 0) {
                printf("[DEBUG] Player %d request: (%d,%d)~(%d,%d)\n", player_id + 1, r1, c1, r2, c2);
                
                if (isValid(r1, c1, r2, c2)) {
                    scores[player_id]++;
                    
                    // 1. VALID 메시지 전송 (정답)
                    char response[100];
                    sprintf(response, "VALID %d %d %d %d %d %d\n", player_id, r1, c1, r2, c2, scores[player_id]);
                    broadcast(response);
                    
                    printf("[INFO] Player %d scored. Turn changed to Player %d.\n", player_id + 1, other_id + 1);
                    
                    // 2. 턴 넘기기
                    current_turn = other_id; 
                    
                    // 3. 턴 변경 알림
                    char turn_msg[50];
                    sprintf(turn_msg, "TURN_CHANGE %d\n", current_turn);
                    broadcast(turn_msg);
                    
                } else {
                    // ★ [수정] 실패 시 턴을 넘기지 않고 다시 시도하도록 함.
                    
                    // 1. 해당 플레이어에게 INVALID 메시지 전송 (다시 시도하라는 신호)
                    char error_msg[50];
                    sprintf(error_msg, "INVALID\n");
                    write(client_fds[player_id], error_msg, strlen(error_msg));
                    
                    // 2. 턴은 그대로 유지 (current_turn = player_id)
                    printf("[INFO] Player %d missed. Turn kept.\n", player_id + 1);
                    
                    // 3. 턴 변경 알림은 보내지 않음 (select가 다시 같은 플레이어를 기다림)
                }
            }
        }
    }

    close(client_fds[0]);
    close(client_fds[1]);
    close(server_fd);
    return 0;
}