/*#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/select.h>
#include "network.h"
#include "game_logic.h"
#include "database.h"

int main() {
    setbuf(stdout, NULL);
    if (!init_database()) exit(1);
    init_board();
    init_server();
    wait_for_players();
    send_board_data();
    
    char buffer[BUFFER_SIZE];
    while (1) {
        int pid = current_turn;
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(client_fds[pid], &read_fds);
        
        if (select(client_fds[pid] + 1, &read_fds, NULL, NULL, NULL) < 0) break;

        if (FD_ISSET(client_fds[pid], &read_fds)) {
            memset(buffer, 0, BUFFER_SIZE);
            if (read(client_fds[pid], buffer, BUFFER_SIZE) <= 0) break;
            
            char cmd[10];
            int r1, c1, r2, c2;
            sscanf(buffer, "%s %d %d %d %d", cmd, &r1, &c1, &r2, &c2);
            
            if (strcmp(cmd, "MOVE") == 0) {
                if (isValid(r1, c1, r2, c2)) {
                    scores[pid]++;
                    char res[100];
                    sprintf(res, "VALID %d %d %d %d %d %d\n", pid, r1, c1, r2, c2, scores[pid]);
                    broadcast(res);
                    current_turn = (current_turn + 1) % 2;
                    char turn[50];
                    sprintf(turn, "TURN_CHANGE %d\n", current_turn);
                    broadcast(turn);
                } else {
                    send_message(pid, "INVALID\n");
                }
            }
        }
    }
    close_server();
    return 0;
}*/

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
    
    // 2. 초기화 단계
    if (!init_database()) exit(1);
    init_board();
    init_server();
    wait_for_players();
    
    // 3. 게임 시작: 보드 데이터 전송
    printf("Sending board data...\n");
    send_board_data();
    
    printf("Game Start! Turn: Player 1\n");
    
    char buffer[BUFFER_SIZE];

    // 4. 메인 게임 루프
    while (1) {
        // 현재 턴인 플레이어뿐만 아니라, 모든 클라이언트의 입력을 감시해야 함 (로그인은 언제든 올 수 있으므로)
        // 하지만 1:1 게임 특성상 로그인 후 게임이 시작되므로, 여기서는 턴 관리 중심으로 구현
        
        /*int pid = current_turn;            // 현재 턴인 플레이어 ID (0 or 1)
        int other_pid = (pid + 1) % 2;     // 상대방 ID*/
        
        // select() 준비
        fd_set read_fds;
        FD_ZERO(&read_fds);
        
        // 현재는 두 플레이어의 입력을 모두 감시하도록 설정 (채팅이나 비동기 명령 처리를 위해)
        // 만약 턴 제어를 엄격하게 하려면 pid만 넣으면 됨
        if (client_fds[0] > 0) FD_SET(client_fds[0], &read_fds);
        if (client_fds[1] > 0) FD_SET(client_fds[1], &read_fds);
        
        int max_fd = (client_fds[0] > client_fds[1]) ? client_fds[0] : client_fds[1];

        // printf("Waiting for input...\n"); // (너무 자주 뜨면 주석 처리)

        // 입력 대기 (Blocking)
        if (select(max_fd + 1, &read_fds, NULL, NULL, NULL) < 0) {
            perror("select error");
            break;
        }

        // 두 플레이어 중 누가 보냈는지 확인
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
                
                // 명령어 파싱
                char cmd[20];
                sscanf(buffer, "%s", cmd); // 첫 단어만 먼저 읽음
                
                // =================================================
                // [1] 로그인 처리 (REQ_LOGIN id pw)
                // =================================================
                if (strcmp(cmd, "REQ_LOGIN") == 0) {
                    char id[50], pw[50];
                    sscanf(buffer, "%*s %s %s", id, pw); // cmd 뒤의 id, pw 읽기
                    
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
                    // 턴 확인: 현재 턴인 플레이어만 MOVE 가능
                    if (i != current_turn) {
                        // 턴 아님 메시지 보내거나 무시
                         continue; 
                    }

                    int r1, c1, r2, c2;
                    sscanf(buffer, "%*s %d %d %d %d", &r1, &c1, &r2, &c2);
                    
                    printf("[DEBUG] Player %d move: (%d,%d)~(%d,%d)\n", i + 1, r1, c1, r2, c2);

                    if (isValid(r1, c1, r2, c2)) {
                        scores[i]++;
                        
                        // 정답 알림 (VALID)
                        char res[100];
                        sprintf(res, "VALID %d %d %d %d %d %d\n", i, r1, c1, r2, c2, scores[i]);
                        broadcast(res);
                        
                        printf("[INFO] Player %d scored.\n", i + 1);

                        // 턴 넘기기
                        current_turn = (current_turn + 1) % 2;
                        
                        // 턴 변경 알림
                        char turn[50];
                        sprintf(turn, "TURN_CHANGE %d\n", current_turn);
                        broadcast(turn);
                        
                    } else {
                        // 실패 시: INVALID만 보내고 턴 유지
                        send_message(i, "INVALID\n");
                        printf("[INFO] Player %d missed. Turn kept.\n", i + 1);
                    }
                }
                
                // =================================================
                // [3] 그 외 명령어 (채팅 등 추가 가능)
                // =================================================
                else {
                    // printf("Unknown command: %s\n", buffer);
                }
            }
        }
    }
    
    close_server();
    return 0;
}