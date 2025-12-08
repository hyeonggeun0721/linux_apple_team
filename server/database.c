#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h> // [필수] Makefile에 -lm 옵션 필요
#include "sqlite3.h"
#include "database.h"

sqlite3 *db;

void hash_password(const char *plain_pw, char *hashed_pw) {
    unsigned int hash = 0x811c9dc5;
    unsigned int prime = 0x01000193;
    for(int i = 0; plain_pw[i] != '\0'; i++) {
        hash = hash ^ plain_pw[i];
        hash = hash * prime;
    }
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
    printf("[DB] Database opened successfully\n");

    // [수정] MMR 기본값 0으로 변경
    char *sql_users = 
        "CREATE TABLE IF NOT EXISTS Users (" \
        "ID TEXT PRIMARY KEY," \
        "PASSWORD TEXT NOT NULL," \
        "NICKNAME TEXT," \
        "MMR INTEGER DEFAULT 0," \
        "TIER TEXT DEFAULT 'BRONZE'," \
        "ONLINE INTEGER DEFAULT 0);"; 
    
    sqlite3_exec(db, sql_users, 0, 0, 0);

    char *sql_history = 
        "CREATE TABLE IF NOT EXISTS History (" \
        "GameID INTEGER PRIMARY KEY AUTOINCREMENT," \
        "Date TEXT," \
        "WinnerID TEXT," \
        "LoserID TEXT," \
        "ScoreW INTEGER," \
        "ScoreL INTEGER);";

    rc = sqlite3_exec(db, sql_history, 0, 0, &errMsg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "[DB Error] History table creation failed: %s\n", errMsg);
        sqlite3_free(errMsg);
        return 0;
    }

    return 1;
}

void close_database() {
    sqlite3_close(db);
}

int create_user(char *id, char *pw, char *nickname) {
    char sql[1024];
    char *errMsg = 0;
    char hashed_pw[32]; 
    hash_password(pw, hashed_pw);
    
    sprintf(sql, "INSERT INTO Users (ID, PASSWORD, NICKNAME) VALUES ('%s', '%s', '%s');", id, hashed_pw, nickname);
    int rc = sqlite3_exec(db, sql, 0, 0, &errMsg);
    if (rc != SQLITE_OK) {
        printf("[DB Error] Create User: %s\n", errMsg); 
        sqlite3_free(errMsg);
        return 0; 
    }
    printf("[DB] Registered User: %s (Start MMR: 0)\n", id); 
    return 1; 
}

int check_login(char *id, char *pw) {
    char sql[1024];
    sqlite3_stmt *stmt;
    char hashed_pw[32];
    hash_password(pw, hashed_pw);

    sprintf(sql, "SELECT * FROM Users WHERE ID='%s' AND PASSWORD='%s';", id, hashed_pw);
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, 0) != SQLITE_OK) return 0; 

    int result = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        result = 1; 
        char update_sql[1024];
        sprintf(update_sql, "UPDATE Users SET ONLINE=1 WHERE ID='%s';", id);
        sqlite3_exec(db, update_sql, 0, 0, 0);
    }
    sqlite3_finalize(stmt); 
    return result;
}

int save_game_result(char *winner_id, char *loser_id, int score_w, int score_l) {
    char sql[1024];
    char *errMsg = 0;
    
    time_t t = time(NULL);
    struct tm tm = *localtime(&t);
    char date_str[30];
    sprintf(date_str, "%04d-%02d-%02d %02d:%02d", 
            tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min);

    printf("[DB Debug] Saving Game: Date=%s, W=%s, L=%s, SW=%d, SL=%d\n", 
            date_str, winner_id, loser_id, score_w, score_l);

    sprintf(sql, "INSERT INTO History (Date, WinnerID, LoserID, ScoreW, ScoreL) VALUES ('%s', '%s', '%s', %d, %d);", 
            date_str, winner_id, loser_id, score_w, score_l);

    int rc = sqlite3_exec(db, sql, 0, 0, &errMsg);
    if (rc != SQLITE_OK) {
        printf("[DB Error] Save Failed: %s\n", errMsg);
        sqlite3_free(errMsg);
        return 0;
    }
    return 1;
}

char* get_user_history(char *user_id) {
    char sql[1024];
    sqlite3_stmt *stmt;
    char *result_buffer = (char*)malloc(4096); 
    if (!result_buffer) return NULL;
    memset(result_buffer, 0, 4096);

    printf("[DB Debug] Fetching history for user: %s\n", user_id);

    sprintf(sql, "SELECT Date, WinnerID, LoserID, ScoreW, ScoreL FROM History WHERE WinnerID='%s' OR LoserID='%s' ORDER BY GameID DESC LIMIT 10;", user_id, user_id);

    if (sqlite3_prepare_v2(db, sql, -1, &stmt, 0) != SQLITE_OK) {
        printf("[DB Error] Prepare Failed: %s\n", sqlite3_errmsg(db));
        free(result_buffer);
        return NULL;
    }

    int count = 0;
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        const char *date = (const char*)sqlite3_column_text(stmt, 0);
        const char *w_id = (const char*)sqlite3_column_text(stmt, 1);
        const char *l_id = (const char*)sqlite3_column_text(stmt, 2);
        int s_w = sqlite3_column_int(stmt, 3);
        int s_l = sqlite3_column_int(stmt, 4);

        char line[200];
        if (strcmp(w_id, user_id) == 0) {
            sprintf(line, "%s|WIN|%s|%d:%d/", date, l_id, s_w, s_l);
        } else {
            sprintf(line, "%s|LOSE|%s|%d:%d/", date, w_id, s_l, s_w);
        }
        strcat(result_buffer, line);
        count++;
    }

    sqlite3_finalize(stmt);
    
    if (count == 0) {
        strcpy(result_buffer, "NONE");
    }
    return result_buffer;
}

// -------------------------------------------------------------
// [랭크 시스템 로직] - 0점 시작 기준
// -------------------------------------------------------------

int get_user_mmr(char *user_id) {
    char sql[256];
    sqlite3_stmt *stmt;
    int mmr = 0; // [수정] 기본값 0

    sprintf(sql, "SELECT MMR FROM Users WHERE ID='%s';", user_id);
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, 0) == SQLITE_OK) {
        if (sqlite3_step(stmt) == SQLITE_ROW) {
            mmr = sqlite3_column_int(stmt, 0);
        }
    }
    sqlite3_finalize(stmt);
    return mmr;
}

// [수정] 0점 기준 티어 구간 재설정
const char* calculate_tier(int mmr) {
    if (mmr < 100) return "BRONZE";
    if (mmr < 200) return "SILVER";
    if (mmr < 300) return "GOLD";
    if (mmr < 400) return "PLATINUM";
    return "DIAMOND";
}

int process_ranked_result(char *winner_id, char *loser_id) {
    int win_mmr = get_user_mmr(winner_id);
    int lose_mmr = get_user_mmr(loser_id);
    
    int K = 32; // 변동 폭
    
    // Elo 공식
    double expected_win = 1.0 / (1.0 + pow(10.0, (double)(lose_mmr - win_mmr) / 400.0));
    double expected_lose = 1.0 / (1.0 + pow(10.0, (double)(win_mmr - lose_mmr) / 400.0));

    int win_change = (int)(K * (1.0 - expected_win));
    int lose_change = (int)(K * (0.0 - expected_lose));

    // 최소 10점 보장 (0점대라 점수 변동폭을 좀 더 체감되게)
    if (win_change < 10) win_change = 10;
    if (lose_change > -10) lose_change = -10;

    int new_win_mmr = win_mmr + win_change;
    int new_lose_mmr = lose_mmr + lose_change;
    
    // 점수는 0점 밑으로 내려가지 않음
    if (new_lose_mmr < 0) new_lose_mmr = 0;

    const char *win_tier = calculate_tier(new_win_mmr);
    const char *lose_tier = calculate_tier(new_lose_mmr);

    printf("[RANK] %s: %d -> %d (+%d) [%s]\n", winner_id, win_mmr, new_win_mmr, win_change, win_tier);
    printf("[RANK] %s: %d -> %d (%d) [%s]\n", loser_id, lose_mmr, new_lose_mmr, lose_change, lose_tier);

    // DB 반영
    char sql[1024];
    sprintf(sql, "UPDATE Users SET MMR=%d, TIER='%s' WHERE ID='%s';", new_win_mmr, win_tier, winner_id);
    sqlite3_exec(db, sql, 0, 0, 0);

    sprintf(sql, "UPDATE Users SET MMR=%d, TIER='%s' WHERE ID='%s';", new_lose_mmr, lose_tier, loser_id);
    sqlite3_exec(db, sql, 0, 0, 0);

    return 1;
}
