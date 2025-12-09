#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/select.h>
#include <arpa/inet.h>
#include <time.h>
#include <signal.h> 
#include "network.h"
#include "database.h"

#define MAX_CLIENTS 30
#define MAX_SESSIONS 15 
#define BOARD_ROWS 10
#define BOARD_COLS 17

typedef struct {
    int is_active;
    int p1_fd;
    int p2_fd;
    char p1_id[50]; 
    char p2_id[50]; 
    int scores[2];
    int current_turn; 
    int board[BOARD_ROWS][BOARD_COLS];
    int owner_board[BOARD_ROWS][BOARD_COLS]; 
} GameSession;

GameSession sessions[MAX_SESSIONS];
int waiting_queue[MAX_CLIENTS];
int queue_count = 0;

typedef struct {
    int fd;
    char id[50];
} ClientInfo;

ClientInfo connected_clients[MAX_CLIENTS];

void init_sessions() {
    for(int i=0; i<MAX_SESSIONS; i++) sessions[i].is_active = 0;
    for(int i=0; i<MAX_CLIENTS; i++) {
        connected_clients[i].fd = 0;
        memset(connected_clients[i].id, 0, 50);
    }
}

char* get_client_id(int fd) {
    for(int i=0; i<MAX_CLIENTS; i++) {
        if(connected_clients[i].fd == fd) return connected_clients[i].id;
    }
    return "Unknown";
}

void register_client_id(int fd, char* id) {
    for(int i=0; i<MAX_CLIENTS; i++) {
        if(connected_clients[i].fd == fd) {
            strcpy(connected_clients[i].id, id);
            return;
        }
    }
    for(int i=0; i<MAX_CLIENTS; i++) {
        if(connected_clients[i].fd == 0) {
            connected_clients[i].fd = fd;
            strcpy(connected_clients[i].id, id);
            return;
        }
    }
}

int find_session_index(int client_fd) {
    for(int i=0; i<MAX_SESSIONS; i++) {
        if (sessions[i].is_active) {
            if (sessions[i].p1_fd == client_fd || sessions[i].p2_fd == client_fd) return i;
        }
    }
    return -1;
}

void start_new_session(int p1, int p2) {
    int s_idx = -1;
    for(int i=0; i<MAX_SESSIONS; i++) {
        if (!sessions[i].is_active) { s_idx = i; break; }
    }
    
    if (s_idx == -1) {
        printf("[ERROR] No free sessions available.\n");
        return;
    }
    
    sessions[s_idx].is_active = 1;
    sessions[s_idx].p1_fd = p1;
    sessions[s_idx].p2_fd = p2;
    strcpy(sessions[s_idx].p1_id, get_client_id(p1));
    strcpy(sessions[s_idx].p2_id, get_client_id(p2));
    
    sessions[s_idx].scores[0] = 0;
    sessions[s_idx].scores[1] = 0;
    sessions[s_idx].current_turn = 0; 
    
    srand(time(NULL) + s_idx); 
    for(int r=0; r<BOARD_ROWS; r++) {
        for(int c=0; c<BOARD_COLS; c++) {
            sessions[s_idx].board[r][c] = (rand() % 9) + 1;
            sessions[s_idx].owner_board[r][c] = -1; 
        }
    }
    
    printf("[GAME] Session %d started: %s vs %s\n", s_idx, sessions[s_idx].p1_id, sessions[s_idx].p2_id);
    
    char msg[50];
    sprintf(msg, "START 0\n"); write(p1, msg, strlen(msg));
    sprintf(msg, "START 1\n"); write(p2, msg, strlen(msg));
    
    char board_msg[4096];
    strcpy(board_msg, "BOARD");
    for(int r=0; r<BOARD_ROWS; r++) {
        for(int c=0; c<BOARD_COLS; c++) {
            char num[5];
            sprintf(num, " %d", sessions[s_idx].board[r][c]);
            strcat(board_msg, num);
        }
    }
    strcat(board_msg, "\n");
    write(p1, board_msg, strlen(board_msg));
    write(p2, board_msg, strlen(board_msg));
    
    char turn[50];
    sprintf(turn, "TURN_CHANGE 0\n");
    write(p1, turn, strlen(turn));
    write(p2, turn, strlen(turn));
}

int check_valid_move(GameSession *s, int r1, int c1, int r2, int c2) {
    if (r1 < 0 || r1 >= BOARD_ROWS || r2 < 0 || r2 >= BOARD_ROWS || 
        c1 < 0 || c1 >= BOARD_COLS || c2 < 0 || c2 >= BOARD_COLS) return 0;
    if (r1 > r2 || c1 > c2) return 0; 

    int sum = 0;
    int r1_h = 0, r2_h = 0, c1_h = 0, c2_h = 0;
    int has_non_zero = 0;

    for(int r=r1; r<=r2; r++) {
        for(int c=c1; c<=c2; c++) {
            if (s->board[r][c] != 0) {
                sum += s->board[r][c];
                has_non_zero = 1;
                if (r == r1) r1_h = 1;
                if (r == r2) r2_h = 1;
                
                if (c == c1) c1_h = 1;
                if (c == c2) c2_h = 1;
            }
        }
    }
    if (sum == 10 && has_non_zero && r1_h && r2_h && c1_h && c2_h) return 1;
    return 0;
}

// ★ [추가] 현재 세션에서 더 이상 가능한 수가 있는지 전수조사
int check_any_possible_move(GameSession *s) {
    for (int r1 = 0; r1 < BOARD_ROWS; r1++) {
        for (int c1 = 0; c1 < BOARD_COLS; c1++) {
            for (int r2 = r1; r2 < BOARD_ROWS; r2++) {
                for (int c2 = c1; c2 < BOARD_COLS; c2++) {
                    if (check_valid_move(s, r1, c1, r2, c2)) {
                        return 1; // 가능한 수 발견
                    }
                }
            }
        }
    }
    return 0; // 더 이상 가능한 수 없음
}

void end_session(int s_idx, int winner_idx_in_session) {
    if (s_idx < 0 || s_idx >= MAX_SESSIONS) return;
    GameSession *s = &sessions[s_idx];
    int p1 = s->p1_fd; int p2 = s->p2_fd;
    int winner_pid = winner_idx_in_session; 

    char *w_id = (winner_pid == 0) ? s->p1_id : s->p2_id;
    char *l_id = (winner_pid == 0) ? s->p2_id : s->p1_id;
    int w_score = s->scores[winner_pid];
    int l_score = s->scores[(winner_pid + 1) % 2];
    
    // 1. 전적 저장
    save_game_result(w_id, l_id, w_score, l_score);

    // 2. 랭크 및 티어 업데이트
    process_ranked_result(w_id, l_id);
    
    char over[100];
    sprintf(over, "GAME_OVER %d %d %d\n", winner_pid, s->scores[0], s->scores[1]);
    if(p1 > 0) write(p1, over, strlen(over));
    if(p2 > 0) write(p2, over, strlen(over));
    
    printf("[GAME] Session %d ended. Winner: P%d\n", s_idx, winner_pid + 1);
    s->is_active = 0; s->p1_fd = 0; s->p2_fd = 0;
}

int main() {
    signal(SIGPIPE, SIG_IGN); 
    setbuf(stdout, NULL);
    if (!init_database()) exit(1);
    init_server(); 
    init_sessions();
    
    int all_clients[MAX_CLIENTS] = {0}; 
    printf("Server started. Waiting...\n");

    while (1) {
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(server_fd, &read_fds);
        int max_fd = server_fd;

        for (int i = 0; i < MAX_CLIENTS; i++) {
            int sd = all_clients[i];
            if (sd > 0) FD_SET(sd, &read_fds);
            if (sd > max_fd) max_fd = sd;
        }

        int activity = select(max_fd + 1, &read_fds, NULL, NULL, NULL);
        if ((activity < 0)) continue;

        if (FD_ISSET(server_fd, &read_fds)) {
            struct sockaddr_in address;
            int addrlen = sizeof(address);
            int new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen);
            if (new_socket >= 0) {
                printf("[INFO] New connection: fd=%d\n", new_socket);
                for (int i = 0; i < MAX_CLIENTS; i++) {
                    if (all_clients[i] == 0) {
                        all_clients[i] = new_socket;
                        connected_clients[i].fd = new_socket;
                        strcpy(connected_clients[i].id, "Guest"); 
                        break;
                    }
                }
            }
        }

        for (int i = 0; i < MAX_CLIENTS; i++) {
            int sd = all_clients[i];
            if (FD_ISSET(sd, &read_fds)) {
                char buffer[BUFFER_SIZE];
                memset(buffer, 0, BUFFER_SIZE);
                int bytes_read = read(sd, buffer, BUFFER_SIZE);
                
                if (bytes_read <= 0) {
                    printf("[INFO] Disconnected: fd=%d\n", sd);
                    close(sd);
                    all_clients[i] = 0;
                    connected_clients[i].fd = 0; 
                    
                    for(int k=0; k<queue_count; k++) {
                        if (waiting_queue[k] == sd) {
                            for(int j=k; j<queue_count-1; j++) waiting_queue[j] = waiting_queue[j+1];
                            queue_count--; break;
                        }
                    }
                    int s_idx = find_session_index(sd);
                    if (s_idx != -1) {
                        int winner = (sessions[s_idx].p1_fd == sd) ? 1 : 0; 
                        end_session(s_idx, winner);
                    }
                } 
                else {
                    char *ptr = strtok(buffer, "\n");
                    while (ptr != NULL) {
                        char cmd[30];
                        sscanf(ptr, "%s", cmd);

                        if (strcmp(cmd, "REQ_LOGIN") == 0) {
                            char id[50], pw[50]; sscanf(ptr, "%*s %s %s", id, pw);
                            if (check_login(id, pw)) {
                                write(sd, "RES_LOGIN_SUCCESS\n", 18);
                                register_client_id(sd, id); 
                            }
                            else write(sd, "RES_LOGIN_FAIL\n", 15);
                        }
                        else if (strcmp(cmd, "REQ_REGISTER") == 0) {
                            char id[50], pw[50], nick[50]; sscanf(ptr, "%*s %s %s %s", id, pw, nick);
                            if (create_user(id, pw, nick)) write(sd, "RES_REGISTER_SUCCESS\n", 21);
                            else write(sd, "RES_REGISTER_FAIL\n", 18);
                        }
                        else if (strcmp(cmd, "REQ_HISTORY") == 0) {
                            char *my_id = get_client_id(sd);
                            char *history_str = get_user_history(my_id);
                            char packet[4096]; memset(packet, 0, 4096);
                            if (history_str) {
                                sprintf(packet, "RES_HISTORY %s\n", history_str);
                                free(history_str);
                            } else {
                                sprintf(packet, "RES_HISTORY NONE\n");
                            }
                            write(sd, packet, strlen(packet));
                        }
                        else if (strcmp(cmd, "REQ_REFRESH") == 0) {
                            char *my_id = get_client_id(sd);
                            int current_mmr = get_user_mmr(my_id);
                            const char *current_tier = calculate_tier(current_mmr);
                            char packet[256];
                            sprintf(packet, "RES_REFRESH %d %s\n", current_mmr, current_tier);
                            write(sd, packet, strlen(packet));
                        }
                        else if (strcmp(cmd, "REQ_QUEUE") == 0) {
                            if (find_session_index(sd) != -1) { ptr = strtok(NULL, "\n"); continue; }
                            int already_queued = 0;
                            for(int k=0; k<queue_count; k++) if(waiting_queue[k]==sd) already_queued=1;
                            if (!already_queued) {
                                waiting_queue[queue_count++] = sd;
                                if (queue_count >= 2) {
                                    int p1 = waiting_queue[0]; int p2 = waiting_queue[1];
                                    for(int k=0; k<queue_count-2; k++) waiting_queue[k] = waiting_queue[k+2];
                                    queue_count -= 2; start_new_session(p1, p2);
                                }
                            }
                        }
                        else if (strcmp(cmd, "CANCEL_QUEUE") == 0) {
                            for(int k=0; k<queue_count; k++) {
                                if (waiting_queue[k] == sd) {
                                    for(int j=k; j<queue_count-1; j++) waiting_queue[j] = waiting_queue[j+1];
                                    queue_count--; break;
                                }
                            }
                        }
                        else if (strcmp(cmd, "SURRENDER") == 0) {
                            int s_idx = find_session_index(sd);
                            if (s_idx != -1) {
                                int winner = (sessions[s_idx].p1_fd == sd) ? 1 : 0; 
                                end_session(s_idx, winner);
                            }
                        }
                        else if (strcmp(cmd, "PASS") == 0) {
                            int s_idx = find_session_index(sd);
                            if (s_idx != -1) {
                                GameSession *s = &sessions[s_idx];
                                int pid = (sd == s->p1_fd) ? 0 : 1;
                                if (pid == s->current_turn) {
                                    s->current_turn = (s->current_turn + 1) % 2;
                                    char turn[50]; sprintf(turn, "TURN_CHANGE %d\n", s->current_turn);
                                    write(s->p1_fd, turn, strlen(turn)); write(s->p2_fd, turn, strlen(turn));
                                }
                            }
                        }
                        else if (strcmp(cmd, "MOVE") == 0) {
                            int s_idx = find_session_index(sd);
                            if (s_idx != -1) {
                                GameSession *s = &sessions[s_idx];
                                int pid = (sd == s->p1_fd) ? 0 : 1;
                                if (pid == s->current_turn) {
                                    int r1, c1, r2, c2; sscanf(ptr, "%*s %d %d %d %d", &r1, &c1, &r2, &c2);
                                    if (r1 > r2) { int temp = r1; r1 = r2; r2 = temp; }
                                    if (c1 > c2) { int temp = c1; c1 = c2; c2 = temp; }
                                    if (check_valid_move(s, r1, c1, r2, c2)) {
                                        int cells_count = 0; int other_pid = (pid + 1) % 2;
                                        for(int r=r1; r<=r2; r++) {
                                            for(int c=c1; c<=c2; c++) {
                                                if (s->owner_board[r][c] == other_pid) s->scores[other_pid]--;
                                                if (s->owner_board[r][c] != pid) { s->owner_board[r][c] = pid; cells_count++; }
                                                s->board[r][c] = 0;
                                            }
                                        }
                                        s->scores[pid] += cells_count;
                                        char res[100]; sprintf(res, "VALID %d %d %d %d %d %d %d\n", pid, r1, c1, r2, c2, s->scores[0], s->scores[1]);
                                        write(s->p1_fd, res, strlen(res)); write(s->p2_fd, res, strlen(res));

                                        // ★ [수정됨] 세션 기반으로 판독 로직 추가
                                        if (check_any_possible_move(s) == 0) {
                                            printf("[GAME] Session %d: No more moves. Game Over.\n", s_idx);
                                            
                                            // 승자 판별 (점수가 높거나 같으면 P1 승리, 필요시 무승부 로직 추가 가능)
                                            int winner = (s->scores[0] >= s->scores[1]) ? 0 : 1;
                                            
                                            // end_session이 이미 broadcast와 DB저장 등을 처리함
                                            end_session(s_idx, winner);
                                            
                                            // 여기서 continue하면 아래의 TURN_CHANGE를 보내지 않고 다음 루프로 감
                                            continue; 
                                        }

                                        s->current_turn = other_pid;
                                        char turn[50]; sprintf(turn, "TURN_CHANGE %d\n", s->current_turn);
                                        write(s->p1_fd, turn, strlen(turn)); write(s->p2_fd, turn, strlen(turn));
                                    } else { write(sd, "INVALID\n", 8); }
                                }
                            }
                        }
                        else if (strcmp(cmd, "CHAT") == 0) {
                            int s_idx = find_session_index(sd);
                            if (s_idx != -1) {
                                GameSession *s = &sessions[s_idx];
                                int pid = (sd == s->p1_fd) ? 0 : 1; 
                                char chat_msg[512];
                                if (sscanf(ptr, "%*s %[^\n]", chat_msg) >= 1) {
                                    char packet[600];
                                    sprintf(packet, "CHAT %d %s\n", pid, chat_msg);
                                    write(s->p1_fd, packet, strlen(packet));
                                    write(s->p2_fd, packet, strlen(packet));
                                }
                            }
                        }
                        
                        ptr = strtok(NULL, "\n");
                    }
                }
            }
        }
    }
    close_server();
    return 0;
}