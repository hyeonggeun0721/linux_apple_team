#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/select.h>
#include <arpa/inet.h>
#include "network.h"
#include "game_logic.h"
#include "database.h"

#define MAX_CLIENTS 30

// 게임 중인 플레이어의 소켓 번호 (매칭된 2명)
int player_fds[2] = {0, 0}; 

// 게임 상태 리셋 (종료 시 호출)
void reset_game_state() {
    // 점수 및 보드 초기화
    scores[0] = 0;
    scores[1] = 0;
    init_board(); 
    
    // 플레이어 자리 비우기 (중요: 그래야 다음 매칭 가능)
    player_fds[0] = 0;
    player_fds[1] = 0;
    current_turn = 0;
    
    // 전역 변수(broadcast용)도 초기화
    client_fds[0] = 0;
    client_fds[1] = 0;
    
    printf("[INFO] Game Reset. Ready for new players.\n");
}

int main() {
    // 1. 초기화
    setbuf(stdout, NULL);
    if (!init_database()) exit(1);
    init_board();
    init_server(); 
    
    // 접속한 모든 클라이언트 소켓을 저장하는 배열
    int all_clients[MAX_CLIENTS] = {0}; 
    
    printf("Server started. Waiting for connections...\n");

    // 2. 메인 루프 (무한 반복)
    while (1) {
        fd_set read_fds;
        FD_ZERO(&read_fds);
        
        // (A) 서버 소켓(신규 접속) 감시 등록
        FD_SET(server_fd, &read_fds);
        int max_fd = server_fd;

        // (B) 연결된 모든 클라이언트 감시 등록
        for (int i = 0; i < MAX_CLIENTS; i++) {
            int sd = all_clients[i];
            if (sd > 0) FD_SET(sd, &read_fds);
            if (sd > max_fd) max_fd = sd;
        }

        // (C) 입력 대기 (Select)
        int activity = select(max_fd + 1, &read_fds, NULL, NULL, NULL);
        if ((activity < 0)) continue;

        // [1] 새로운 접속 처리 (Accept)
        if (FD_ISSET(server_fd, &read_fds)) {
            struct sockaddr_in address;
            int addrlen = sizeof(address);
            int new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen);
            
            if (new_socket >= 0) {
                printf("[INFO] New connection: fd=%d\n", new_socket);
                // 빈 자리에 저장
                for (int i = 0; i < MAX_CLIENTS; i++) {
                    if (all_clients[i] == 0) {
                        all_clients[i] = new_socket;
                        break;
                    }
                }
            }
        }

        // [2] 기존 클라이언트들의 요청 처리
        for (int i = 0; i < MAX_CLIENTS; i++) {
            int sd = all_clients[i];
            
            if (FD_ISSET(sd, &read_fds)) {
                char buffer[BUFFER_SIZE];
                memset(buffer, 0, BUFFER_SIZE);
                int bytes_read = read(sd, buffer, BUFFER_SIZE);
                
                // 연결 종료 처리
                if (bytes_read <= 0) {
                    printf("[INFO] Disconnected: fd=%d\n", sd);
                    close(sd);
                    all_clients[i] = 0;
                    
                    // 게임 중이던 플레이어가 나가면 게임 리셋
                    if (sd == player_fds[0] || sd == player_fds[1]) {
                        int winner = (sd == player_fds[0]) ? 1 : 0; // 남은 사람이 승리
                        char over[100];
                        sprintf(over, "GAME_OVER %d %d %d\n", winner, scores[0], scores[1]);
                        
                        // 남은 사람에게 전송
                        if (player_fds[winner] > 0) write(player_fds[winner], over, strlen(over));
                        
                        reset_game_state();
                    }
                } 
                // 데이터 처리
                else {
                    char cmd[30];
                    sscanf(buffer, "%s", cmd);

                    // -------------------------------------------------
                    // [로그인 / 회원가입]
                    // -------------------------------------------------
                    if (strcmp(cmd, "REQ_LOGIN") == 0) {
                        char id[50], pw[50];
                        sscanf(buffer, "%*s %s %s", id, pw);
                        if (check_login(id, pw)) write(sd, "RES_LOGIN_SUCCESS\n", 18);
                        else write(sd, "RES_LOGIN_FAIL\n", 15);
                    }
                    else if (strcmp(cmd, "REQ_REGISTER") == 0) {
                        char id[50], pw[50], nick[50];
                        sscanf(buffer, "%*s %s %s %s", id, pw, nick);
                        if (create_user(id, pw, nick)) write(sd, "RES_REGISTER_SUCCESS\n", 21);
                        else write(sd, "RES_REGISTER_FAIL\n", 18);
                    }

                    // -------------------------------------------------
                    // [매칭 대기열] REQ_QUEUE
                    // -------------------------------------------------
                    else if (strcmp(cmd, "REQ_QUEUE") == 0) {
                        // 이미 게임 중이면 무시
                        if (sd == player_fds[0] || sd == player_fds[1]) continue;

                        if (player_fds[0] == 0) {
                            player_fds[0] = sd;
                            printf("[GAME] P1 joined (fd=%d)\n", sd);
                        } else if (player_fds[1] == 0 && player_fds[0] != sd) {
                            player_fds[1] = sd;
                            printf("[GAME] P2 joined (fd=%d). Game Start!\n", sd);
                            
                            // 1. 게임 시작 신호
                            char msg[50];
                            sprintf(msg, "START 0\n"); write(player_fds[0], msg, strlen(msg));
                            sprintf(msg, "START 1\n"); write(player_fds[1], msg, strlen(msg));
                            
                            // 2. 전역 변수 업데이트 (network.c의 client_fds 등)
                            client_fds[0] = player_fds[0];
                            client_fds[1] = player_fds[1];
                            
                            // 3. 보드 전송
                            send_board_data();
                            
                            // 4. 첫 턴 알림
                            char turn[50];
                            sprintf(turn, "TURN_CHANGE %d\n", current_turn);
                            broadcast(turn);
                        }
                    }

                    // -------------------------------------------------
                    // [항복] SURRENDER (누구나 가능)
                    // -------------------------------------------------
                    else if (strcmp(cmd, "SURRENDER") == 0) {
                         if (sd == player_fds[0] || sd == player_fds[1]) {
                            printf("[GAME] Player fd=%d surrendered.\n", sd);
                            int winner = (sd == player_fds[0]) ? 1 : 0; // 상대방 승리
                            
                            char over[100];
                            sprintf(over, "GAME_OVER %d %d %d\n", winner, scores[0], scores[1]);
                            broadcast(over);
                            
                            reset_game_state();
                         }
                    }

                    // -------------------------------------------------
                    // [스킵] PASS (내 턴일 때만)
                    // -------------------------------------------------
                    else if (strcmp(cmd, "PASS") == 0) {
                        int pid = -1;
                        if (sd == player_fds[0]) pid = 0;
                        else if (sd == player_fds[1]) pid = 1;

                        if (pid != -1 && pid == current_turn) {
                            printf("[GAME] Player %d passed turn.\n", pid + 1);
                            current_turn = (current_turn + 1) % 2;
                            
                            char turn[50];
                            sprintf(turn, "TURN_CHANGE %d\n", current_turn);
                            broadcast(turn);
                        }
                    }

                    // -------------------------------------------------
                    // [이동] MOVE (내 턴일 때만)
                    // -------------------------------------------------
                    else if (strcmp(cmd, "MOVE") == 0) {
                        int pid = -1;
                        if (sd == player_fds[0]) pid = 0;
                        else if (sd == player_fds[1]) pid = 1;

                        if (pid != -1 && pid == current_turn) {
                            int r1, c1, r2, c2;
                            sscanf(buffer, "%*s %d %d %d %d", &r1, &c1, &r2, &c2);
                            
                            if (isValid(r1, c1, r2, c2)) {
                                // 점수 계산 (칸 수 + 뺏기)
                                int cells_count = 0;
                                int other_pid = (pid + 1) % 2;
                                for(int r=r1; r<=r2; r++) {
                                    for(int c=c1; c<=c2; c++) {
                                        if (owner_board[r][c] == other_pid) scores[other_pid]--; 
                                        owner_board[r][c] = pid;
                                        cells_count++;
                                    }
                                }
                                scores[pid] += cells_count;
                                
                                char res[100];
                                sprintf(res, "VALID %d %d %d %d %d %d %d\n", pid, r1, c1, r2, c2, scores[0], scores[1]);
                                broadcast(res);
                                
                                current_turn = other_pid;
                                char turn[50];
                                sprintf(turn, "TURN_CHANGE %d\n", current_turn);
                                broadcast(turn);
                                
                            } else {
                                write(sd, "INVALID\n", 8);
                            }
                        }
                    }
                }
            }
        }
    }
    
    close_server();
    return 0;
}