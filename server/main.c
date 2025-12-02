#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/select.h>
#include "network.h"
#include "game_logic.h"
#include "database.h"

#define MAX_CLIENTS 30  // 최대 동시 접속자 수

int main() {
    // 1. 버퍼링 해제
    setbuf(stdout, NULL);
    
    // 2. 초기화
    if (!init_database()) exit(1);
    init_board();
    init_server(); // socket(), bind(), listen()만 수행
    
    // 클라이언트 소켓 관리용 배열 (0으로 초기화)
    int all_clients[MAX_CLIENTS] = {0}; 
    
    // 게임 플레이어 매핑 (누가 P1, P2인지 소켓 FD 저장)
    int player_fds[2] = {0, 0}; 
    
    printf("Server started. Waiting for connections...\n");

    // 3. 메인 루프 (접속 대기 + 데이터 처리 동시에 수행)
    while (1) {
        fd_set read_fds;
        FD_ZERO(&read_fds);
        
        // (1) 서버 소켓(신규 접속) 감시 등록
        FD_SET(server_fd, &read_fds);
        int max_fd = server_fd;

        // (2) 연결된 모든 클라이언트 감시 등록
        for (int i = 0; i < MAX_CLIENTS; i++) {
            int sd = all_clients[i];
            if (sd > 0) FD_SET(sd, &read_fds);
            if (sd > max_fd) max_fd = sd;
        }

        // (3) Select 대기
        int activity = select(max_fd + 1, &read_fds, NULL, NULL, NULL);
        if ((activity < 0)) {
            perror("select error");
            continue;
        }

        // (4) 새로운 접속 처리 (Accept)
        if (FD_ISSET(server_fd, &read_fds)) {
            struct sockaddr_in address;
            int addrlen = sizeof(address);
            int new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen);
            
            if (new_socket < 0) {
                perror("accept");
            } else {
                printf("[INFO] New connection: fd=%d, ip=%s\n", new_socket, inet_ntoa(address.sin_addr));
                
                // 빈 자리에 소켓 저장
                for (int i = 0; i < MAX_CLIENTS; i++) {
                    if (all_clients[i] == 0) {
                        all_clients[i] = new_socket;
                        break;
                    }
                }
            }
        }

        // (5) 기존 클라이언트들의 요청 처리
        for (int i = 0; i < MAX_CLIENTS; i++) {
            int sd = all_clients[i];
            
            if (FD_ISSET(sd, &read_fds)) {
                char buffer[BUFFER_SIZE];
                memset(buffer, 0, BUFFER_SIZE);
                
                int bytes_read = read(sd, buffer, BUFFER_SIZE);
                
                // 연결 종료 처리
                if (bytes_read == 0) {
                    printf("[INFO] Host disconnected: fd=%d\n", sd);
                    close(sd);
                    all_clients[i] = 0;
                    
                    // 만약 게임 중이던 플레이어라면 게임 종료 처리 필요
                    if (sd == player_fds[0]) player_fds[0] = 0;
                    if (sd == player_fds[1]) player_fds[1] = 0;
                }
                
                // 데이터 처리
                else {
                    // 명령어 파싱
                    char cmd[30];
                    sscanf(buffer, "%s", cmd);

                    // --- [회원가입] ---
                    if (strcmp(cmd, "REQ_REGISTER") == 0) {
                        char id[50], pw[50], nick[50];
                        sscanf(buffer, "%*s %s %s %s", id, pw, nick);
                        printf("[REGISTER] ID: %s, Nick: %s\n", id, nick);
                        
                        if (create_user(id, pw, nick)) {
                            write(sd, "RES_REGISTER_SUCCESS\n", 21);
                        } else {
                            write(sd, "RES_REGISTER_FAIL\n", 18);
                        }
                    }
                    
                    // --- [로그인] ---
                    else if (strcmp(cmd, "REQ_LOGIN") == 0) {
                        char id[50], pw[50];
                        sscanf(buffer, "%*s %s %s", id, pw);
                        printf("[LOGIN] ID: %s\n", id);
                        
                        if (check_login(id, pw)) {
                            write(sd, "RES_LOGIN_SUCCESS\n", 18);
                        } else {
                            write(sd, "RES_LOGIN_FAIL\n", 15);
                        }
                    }

                    // --- [게임 매칭 대기열] (임시 구현: 접속하면 바로 P1, P2 할당) ---
                    else if (strcmp(cmd, "REQ_QUEUE") == 0) {
                        if (player_fds[0] == 0) {
                            player_fds[0] = sd;
                            write(sd, "WAITING\n", 8); // 대기 중
                            printf("[GAME] Player 1 joined (fd=%d)\n", sd);
                        } else if (player_fds[1] == 0) {
                            player_fds[1] = sd;
                            printf("[GAME] Player 2 joined (fd=%d). Game Start!\n", sd);
                            
                            // 두 명 다 찼으므로 게임 시작 신호 전송
                            // 1. P1에게 START 0 전송
                            char msg1[50]; sprintf(msg1, "START 0\n");
                            write(player_fds[0], msg1, strlen(msg1));
                            
                            // 2. P2에게 START 1 전송
                            char msg2[50]; sprintf(msg2, "START 1\n");
                            write(player_fds[1], msg2, strlen(msg2));
                            
                            // 3. 보드 데이터 전송 (전역 변수 client_fds 업데이트 필요)
                            client_fds[0] = player_fds[0];
                            client_fds[1] = player_fds[1];
                            send_board_data(); 
                            
                            // 4. 턴 알림
                            char turn[50];
                            sprintf(turn, "TURN_CHANGE %d\n", current_turn);
                            broadcast(turn);
                        }
                    }

                    // --- [게임 이동] ---
                    else if (strcmp(cmd, "MOVE") == 0) {
                        // 현재 보낸 사람이 누구인지 식별 (0번 플레이어? 1번 플레이어?)
                        int pid = -1;
                        if (sd == player_fds[0]) pid = 0;
                        else if (sd == player_fds[1]) pid = 1;

                        if (pid != -1 && pid == current_turn) {
                            int r1, c1, r2, c2;
                            sscanf(buffer, "%*s %d %d %d %d", &r1, &c1, &r2, &c2);
                            
                            if (isValid(r1, c1, r2, c2)) {
                                // 점수 계산 로직
                                int cells = 0;
                                int other_pid = (pid + 1) % 2;
                                for(int r=r1; r<=r2; r++) {
                                    for(int c=c1; c<=c2; c++) {
                                        if (owner_board[r][c] == other_pid) scores[other_pid]--;
                                        owner_board[r][c] = pid;
                                        cells++;
                                    }
                                }
                                scores[pid] += cells;

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