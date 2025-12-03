#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sqlite3.h"
#include "database.h"

sqlite3 *db;

// [추가] 간단한 해시 함수 (비밀번호 암호화용)
// FNV-1a 알고리즘을 변형하여 문자열을 16진수 해시값으로 변환
void hash_password(const char *plain_pw, char *hashed_pw) {
    unsigned int hash = 0x811c9dc5;
    unsigned int prime = 0x01000193;
    
    for(int i = 0; plain_pw[i] != '\0'; i++) {
        hash = hash ^ plain_pw[i];
        hash = hash * prime;
    }
    // 숫자를 8자리 16진수 문자열로 변환 (예: "a1b2c3d4")
    sprintf(hashed_pw, "%08x", hash);
}

int init_database() {
    char *errMsg = 0;
    int rc;

    rc = sqlite3_open(DB_NAME, &db);
    if (rc) {
        fprintf(stderr, "Can't open database: %s\n", sqlite3_errmsg(db));
        return 0;
    }
    printf("Opened database successfully\n");

    // Users 테이블
    char *sql_users = 
        "CREATE TABLE IF NOT EXISTS Users (" \
        "ID TEXT PRIMARY KEY," \
        "PASSWORD TEXT NOT NULL," \
        "NICKNAME TEXT," \
        "MMR INTEGER DEFAULT 1000," \
        "TIER TEXT DEFAULT 'BRONZE'," \
        "ONLINE INTEGER DEFAULT 0);"; 

    rc = sqlite3_exec(db, sql_users, 0, 0, &errMsg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "SQL error (Users): %s\n", errMsg);
        sqlite3_free(errMsg);
        return 0;
    }

    // History 테이블
    char *sql_history = 
        "CREATE TABLE IF NOT EXISTS History (" \
        "GameID INTEGER PRIMARY KEY AUTOINCREMENT," \
        "WinnerID TEXT," \
        "LoserID TEXT," \
        "ReplayData TEXT);";

    rc = sqlite3_exec(db, sql_history, 0, 0, &errMsg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "SQL error (History): %s\n", errMsg);
        sqlite3_free(errMsg);
        return 0;
    }

    printf("Database & Tables initialized.\n");
    return 1;
}

void close_database() {
    sqlite3_close(db);
}

// [수정] 회원가입 (암호화 적용)
int create_user(char *id, char *pw, char *nickname) {
    char sql[256];
    char *errMsg = 0;
    char hashed_pw[32]; // 암호화된 비번 저장 공간

    // 1. 비밀번호 암호화
    hash_password(pw, hashed_pw);
    
    // 2. 암호화된 비밀번호(hashed_pw)를 저장
    sprintf(sql, "INSERT INTO Users (ID, PASSWORD, NICKNAME) VALUES ('%s', '%s', '%s');", id, hashed_pw, nickname);

    int rc = sqlite3_exec(db, sql, 0, 0, &errMsg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Insert error: %s\n", errMsg);
        sqlite3_free(errMsg);
        return 0; 
    }
    printf("[DB] Registered %s (PW: %s -> %s)\n", id, pw, hashed_pw); // 로그로 암호화 확인
    return 1; 
}

// [수정] 로그인 확인 (암호화 적용)
int check_login(char *id, char *pw) {
    char sql[256];
    sqlite3_stmt *stmt;
    char hashed_pw[32];

    // 1. 입력된 비밀번호를 똑같은 방식으로 암호화
    hash_password(pw, hashed_pw);
    
    // 2. 암호화된 비밀번호로 DB 조회
    sprintf(sql, "SELECT * FROM Users WHERE ID='%s' AND PASSWORD='%s';", id, hashed_pw);

    if (sqlite3_prepare_v2(db, sql, -1, &stmt, 0) != SQLITE_OK) {
        return 0; 
    }

    int result = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        result = 1; // 성공
        
        // 로그인 상태 업데이트
        char update_sql[128];
        sprintf(update_sql, "UPDATE Users SET ONLINE=1 WHERE ID='%s';", id);
        sqlite3_exec(db, update_sql, 0, 0, 0);
    }

    sqlite3_finalize(stmt); 
    return result;
}