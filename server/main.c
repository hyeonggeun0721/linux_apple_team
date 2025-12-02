#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/select.h>
#include "network.h"
#include "game_logic.h"
#include "database.h"

int main() {
    // 1. 버퍼링 해제 (로그 즉시 출력)
    setbuf(stdout, NULL);
    
    // 2. 초기화
    if (!init_database()) exit(1);
    init_board();
    init_server();
    wait_for_players();
    
    // 3. 게임 시작 및 보드 전송
    printf("Sending board data...\n");
    send_board_data();
    
    printf("Game Start! Turn: Player 1\n");
    
    char buffer[BUFFER_SIZE];

    // 4. 메인 루프
    while (1) {
        fd_set read_fds;
        FD_ZERO(&read_fds);
        
        // 두 플레이어 모두 감시 (로그인, 이동 등 비동기 이벤트 처리)
        if (client_fds[0] > 0) FD_SET(client_fds[0], &read_fds);
        if (client_fds[1] > 0) FD_SET(client_fds[1], &read_fds);
        
        int max_fd = (client_fds[0] > client_fds[1]) ? client_fds[0] : client_fds[1];

        if (select(max_fd + 1, &read_fds, NULL, NULL, NULL) < 0) {
            perror("select error");
            break;
        }

        for (int i = 0; i < 2; i++) {
            if (client_fds[i] > 0 && FD_ISSET(client_fds[i], &read_fds)) {
                
                memset(buffer, 0, BUFFER_SIZE);
                int bytes_read = read(client_fds[i], buffer, BUFFER_SIZE);
                
                if (bytes_read <= 0) {
                    printf("Player %d disconnected.\n", i + 1);
                    close(client_fds[i]);
                    client_fds[i] = 0;
                    continue;
                }
                
                char cmd[20];
                sscanf(buffer, "%s", cmd); 
                
                // =================================================
                // [1] 로그인 처리 (REQ_LOGIN id pw)
                // =================================================
                if (strcmp(cmd, "REQ_LOGIN") == 0) {
                    char id[50], pw[50];
                    sscanf(buffer, "%*s %s %s", id, pw);
                    
                    printf("[DEBUG] Login request from P%d: %s\n", i + 1, id);
                    
                    if (check_login(id, pw)) {
                        send_message(i, "RES_LOGIN SUCCESS\n");
                        printf("[INFO] Player %d (%s) logged in.\n", i + 1, id);
                    } else {
                        send_message(i, "RES_LOGIN FAIL\n");
                        printf("[INFO] Login failed for Player %d.\n", i + 1);
                    }
                }

                // =================================================
                // [2] 게임 이동 처리 (MOVE r1 c1 r2 c2)
                // =================================================
                else if (strcmp(cmd, "MOVE") == 0) {
                    // 턴 체크: 내 턴이 아니면 무시
                    if (i != current_turn) {
                         continue; 
                    }

                    int pid = i;                 // 현재 플레이어 ID
                    int other_pid = (i + 1) % 2; // 상대방 ID

                    int r1, c1, r2, c2;
                    sscanf(buffer, "%*s %d %d %d %d", &r1, &c1, &r2, &c2);
                    
                    printf("[DEBUG] Player %d move: (%d,%d)~(%d,%d)\n", pid + 1, r1, c1, r2, c2);

                    if (isValid(r1, c1, r2, c2)) {
                        // [점수 로직] 칸 수만큼 더하고, 뺏은 만큼 깎기
                        int cells_count = 0;
                        // 이미 isValid에서 board[][]는 0으로 초기화되었지만, owner_board 갱신 필요
                        // isValid는 검증만 하고 board 수정은 여기서 하거나 game_logic으로 위임하는 게 좋지만
                        // 현재 구조상 isValid가 board를 0으로 만듦.
                        // 여기서는 owner_board를 업데이트하고 점수 계산.
                        
                        for(int r = r1; r <= r2; r++) {
                            for(int c = c1; c <= c2; c++) {
                                // 상대방 땅이면 상대 점수 깎기
                                if (owner_board[r][c] == other_pid) {
                                    scores[other_pid]--; 
                                }
                                // 내 땅으로 변경
                                owner_board[r][c] = pid;
                                cells_count++;
                            }
                        }
                        // 내 점수는 먹은 칸 수만큼 증가
                        scores[pid] += cells_count;
                        
                        // VALID 메시지로 두 명의 점수 모두 전송
                        char res[100];
                        sprintf(res, "VALID %d %d %d %d %d %d %d\n", pid, r1, c1, r2, c2, scores[0], scores[1]);
                        broadcast(res);
                        
                        printf("[INFO] Player %d scored +%d. Scores: %d vs %d\n", pid + 1, cells_count, scores[0], scores[1]);

                        // 턴 넘기기 (성공 시)
                        current_turn = other_pid;
                        
                        char turn[50];
                        sprintf(turn, "TURN_CHANGE %d\n", current_turn);
                        broadcast(turn);
                        
                    } else {
                        // 실패 시: INVALID만 보내고 턴 유지
                        send_message(pid, "INVALID\n");
                        printf("[INFO] Player %d missed. Turn kept.\n", pid + 1);
                    }
                }
            }
        }
    }
    
    close_server();
    return 0;
}