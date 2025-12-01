#include <stdio.h>
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
}