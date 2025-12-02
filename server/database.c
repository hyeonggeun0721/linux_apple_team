#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sqlite3.h"
#include "database.h"

sqlite3 *db;

// DB 초기화 및 테이블 생성
int init_database() {
    char *errMsg = 0;
    int rc;

    // 1. DB 파일 열기 (없으면 생성됨)
    rc = sqlite3_open(DB_NAME, &db);
    if (rc) {
        fprintf(stderr, "Can't open database: %s\n", sqlite3_errmsg(db));
        return 0;
    }
    printf("Opened database successfully\n");

    // 2. Users 테이블 생성 SQL [cite: 1417]
    char *sql_users = 
        "CREATE TABLE IF NOT EXISTS Users (" \
        "ID TEXT PRIMARY KEY," \
        "PASSWORD TEXT NOT NULL," \
        "NICKNAME TEXT," \
        "MMR INTEGER DEFAULT 1000," \
        "TIER TEXT DEFAULT 'BRONZE');";

    // 3. 실행
    rc = sqlite3_exec(db, sql_users, 0, 0, &errMsg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "SQL error (Users): %s\n", errMsg);
        sqlite3_free(errMsg);
        return 0;
    }

    // 4. History 테이블 생성 SQL [cite: 1418]
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

    printf("Tables created successfully\n");
    return 1;
}

void close_database() {
    sqlite3_close(db);
}

// 회원가입 함수
int create_user(char *id, char *pw, char *nickname) {
    char sql[256];
    char *errMsg = 0;
    
    sprintf(sql, "INSERT INTO Users (ID, PASSWORD, NICKNAME) VALUES ('%s', '%s', '%s');", id, pw, nickname);

    int rc = sqlite3_exec(db, sql, 0, 0, &errMsg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Insert error: %s\n", errMsg);
        sqlite3_free(errMsg);
        return 0; // 실패 (중복 ID 등)
    }
    return 1; // 성공
}

// 로그인 확인 함수 (성공: 1, 실패: 0)
int check_login(char *id, char *pw) {
    char sql[256];
    sqlite3_stmt *stmt;
    
    // SQL: Users 테이블에서 ID와 PW가 일치하는지 조회
    sprintf(sql, "SELECT * FROM Users WHERE ID='%s' AND PASSWORD='%s';", id, pw);

    // 쿼리 준비
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, 0) != SQLITE_OK) {
        return 0; // DB 에러
    }

    // 결과 확인 (한 줄이라도 나오면 성공)
    int result = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        result = 1; // 로그인 성공
    }

    sqlite3_finalize(stmt); // 정리
    return result;
}