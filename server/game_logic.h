#ifndef GAME_LOGIC_H
#define GAME_LOGIC_H

#define ROWS 10
#define COLS 17

extern int board[ROWS][COLS];
extern int scores[2];
extern int current_turn;

// [추가] 각 칸의 주인을 저장하는 배열 (0: P1, 1: P2, -1: 없음)
extern int owner_board[ROWS][COLS];

void init_board();
int isValid(int r1, int c1, int r2, int c2);
void send_board_data();
#endif