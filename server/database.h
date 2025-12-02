#ifndef DATABASE_H
#define DATABASE_H

#include "sqlite3.h"

// DB 파일 이름
#define DB_NAME "game.db"

// 전역 DB 객체 (필요시)
extern sqlite3 *db;

// 함수 원형
int init_database();
void close_database();
int create_user(char *id, char *pw, char *nickname);
int check_login(char *id, char *pw);
// 추후 전적 저장 함수 등 추가 가능

#endif