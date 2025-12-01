#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "game_logic.h"
#include "network.h"

int board[ROWS][COLS];
int scores[2] = {0, 0};
int current_turn = 0;

void init_board() {
    srand(time(NULL));
    for(int i=0; i<ROWS; i++) for(int j=0; j<COLS; j++) board[i][j] = (rand() % 9) + 1;
}

void send_board_data() {
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
}

int isValid(int r1, int c1, int r2, int c2) {
    if (r1 < 0 || r1 >= ROWS || r2 < 0 || r2 >= ROWS || c1 < 0 || c1 >= COLS || c2 < 0 || c2 >= COLS) return 0;
    int sum = 0, r1_h = 0, r2_h = 0, c1_h = 0, c2_h = 0, all_z = 1;
    for (int r = r1; r <= r2; r++) {
        for (int c = c1; c <= c2; c++) {
            if (board[r][c] != 0) {
                all_z = 0; sum += board[r][c];
                if (r == r1) r1_h = 1; if (r == r2) r2_h = 1;
                if (c == c1) c1_h = 1; if (c == c2) c2_h = 1;
            }
        }
    }
    if (all_z) return 0;
    if (sum == 10 && r1_h && r2_h && c1_h && c2_h) {
        for (int r = r1; r <= r2; r++) for (int c = c1; c <= c2; c++) board[r][c] = 0;
        return 1;
    }
    return 0;
}