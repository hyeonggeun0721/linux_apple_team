#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sqlite3.h"
#include "database.h"

sqlite3 *db;

// DB 초기화 및 테이블 4개 생성
int init_database() {
    char *errMsg = 0;
    int rc;

    rc = sqlite3_open(DB_NAME, &db);
    if (rc) {
        fprintf(stderr, "Can't open database: %s\n", sqlite3_errmsg(db));
        return 0;
    }

    // 1. Users 테이블
    char *sql_users = 
        "CREATE TABLE IF NOT EXISTS Users (" \
        "ID TEXT PRIMARY KEY," \
        "PASSWORD TEXT NOT NULL," \
        "NICKNAME TEXT," \
        "MMR INTEGER DEFAULT 1000," \
        "TIER TEXT DEFAULT 'BRONZE'," \
        "ONLINE INTEGER DEFAULT 0);"; // 0:Offline, 1:Online

    sqlite3_exec(db, sql_users, 0, 0, &errMsg);

    // 2. Friends 테이블 (친구 관계)
    char *sql_friends = 
        "CREATE TABLE IF NOT EXISTS Friends (" \
        "USER_ID TEXT," \
        "FRIEND_ID TEXT," \
        "PRIMARY KEY (USER_ID, FRIEND_ID));";

    sqlite3_exec(db, sql_friends, 0, 0, &errMsg);

    // 3. ChatLogs 테이블 (채팅 기록)
    char *sql_chat = 
        "CREATE TABLE IF NOT EXISTS ChatLogs (" \
        "LOG_ID INTEGER PRIMARY KEY AUTOINCREMENT," \
        "SENDER_ID TEXT," \
        "RECEIVER_ID TEXT," \
        "MESSAGE TEXT," \
        "TIMESTAMP DATETIME DEFAULT CURRENT_TIMESTAMP);";

    sqlite3_exec(db, sql_chat, 0, 0, &errMsg);

    // 4. History 테이블
    char *sql_history = 
        "CREATE TABLE IF NOT EXISTS History (" \
        "GameID INTEGER PRIMARY KEY AUTOINCREMENT," \
        "WinnerID TEXT," \
        "LoserID TEXT," \
        "ReplayData TEXT);";

    sqlite3_exec(db, sql_history, 0, 0, &errMsg);

    printf("Database & Tables initialized.\n");
    return 1;
}

void close_database() {
    sqlite3_close(db);
}

// 회원가입 함수 (성공: 1, 실패: 0)
int create_user(char *id, char *pw, char *nickname) {
    char sql[512];
    char *errMsg = 0;
    
    // SQL Injection 방지 처리는 생략함 (학습용)
    // Users 테이블에 데이터 삽입
    sprintf(sql, "INSERT INTO Users (ID, PASSWORD, NICKNAME, MMR, TIER, ONLINE) "
                 "VALUES ('%s', '%s', '%s', 1000, 'BRONZE', 0);", id, pw, nickname);

    // 쿼리 실행
    int rc = sqlite3_exec(db, sql, 0, 0, &errMsg);
    
    if (rc != SQLITE_OK) {
        // 실패 원인 출력 (주로 ID 중복)
        fprintf(stderr, "SQL error (Register): %s\n", errMsg);
        sqlite3_free(errMsg);
        return 0; // 실패
    }
    
    printf("[DB] New user registered: %s (%s)\n", id, nickname);
    return 1; // 성공
}

// 로그인 확인 (성공 시 ONLINE=1로 변경)
int check_login(char *id, char *pw) {
    char sql[256];
    sqlite3_stmt *stmt;
    
    sprintf(sql, "SELECT * FROM Users WHERE ID='%s' AND PASSWORD='%s';", id, pw);
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, 0) != SQLITE_OK) return 0;

    int result = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        result = 1;
        // 로그인 상태 업데이트
        char update_sql[128];
        sprintf(update_sql, "UPDATE Users SET ONLINE=1 WHERE ID='%s';", id);
        sqlite3_exec(db, update_sql, 0, 0, 0);
    }
    sqlite3_finalize(stmt); 
    return result;
}

// 로그아웃 처리
void user_logout(char *id) {
    char sql[128];
    sprintf(sql, "UPDATE Users SET ONLINE=0 WHERE ID='%s';", id);
    sqlite3_exec(db, sql, 0, 0, 0);
}

// [신규] 친구 추가 함수
int add_friend(char *my_id, char *friend_id) {
    char sql[256];
    
    // 친구 ID가 존재하는지 먼저 확인해야 함 (생략 가능하지만 추천)
    
    sprintf(sql, "INSERT INTO Friends (USER_ID, FRIEND_ID) VALUES ('%s', '%s');", my_id, friend_id);
    return (sqlite3_exec(db, sql, 0, 0, 0) == SQLITE_OK);
}

// [신규] 친구 목록 가져오기 (콤마로 구분된 문자열로 반환)
// 예: "friend1,friend2,friend3"
void get_friend_list(char *my_id, char *buffer) {
    char sql[256];
    sqlite3_stmt *stmt;
    
    sprintf(sql, "SELECT FRIEND_ID FROM Friends WHERE USER_ID='%s';", my_id);
    
    strcpy(buffer, ""); // 버퍼 초기화
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, 0) == SQLITE_OK) {
        while (sqlite3_step(stmt) == SQLITE_ROW) {
            const unsigned char *fid = sqlite3_column_text(stmt, 0);
            strcat(buffer, (const char*)fid);
            strcat(buffer, ",");
        }
    }
    sqlite3_finalize(stmt);
}