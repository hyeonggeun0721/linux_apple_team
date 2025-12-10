// server/database.h

#ifndef DATABASE_H
#define DATABASE_H

#include "sqlite3.h"

// DB 파일 이름
#define DB_NAME "game.db"

// 전역 DB 객체
extern sqlite3 *db;

// 기본 함수
int init_database();
void close_database();
int create_user(char *id, char *pw, char *nickname);
int check_login(char *id, char *pw);
void hash_password(const char *plain_pw, char *hashed_pw);

// 전적 및 랭크 시스템 함수
int save_game_result(char *winner_id, char *loser_id, int score_w, int score_l);
char* get_user_history(char *user_id);

// 랭크 계산 및 조회
int process_ranked_result(char *winner_id, char *loser_id);
int get_user_mmr(char *user_id);
const char* calculate_tier(int mmr);

#endif
