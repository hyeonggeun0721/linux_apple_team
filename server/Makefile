CC = gcc
CFLAGS = -Wall -g
# [중요] -lm 추가 (Elo 계산 시 pow 함수 사용을 위해 필수)
LIBS = -lpthread -ldl -lm

TARGET = server
OBJS = main.o network.o game_logic.o database.o sqlite3.o

# 기본 타겟
all: $(TARGET)

# 서버 실행 파일 생성 (링크 단계)
$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJS) $(LIBS)

# 개별 파일 컴파일
main.o: main.c network.h database.h
	$(CC) $(CFLAGS) -c main.c

network.o: network.c network.h
	$(CC) $(CFLAGS) -c network.c

game_logic.o: game_logic.c game_logic.h
	$(CC) $(CFLAGS) -c game_logic.c

database.o: database.c database.h sqlite3.h
	$(CC) $(CFLAGS) -c database.c

# SQLite는 컴파일 시간이 좀 걸리므로 별도 처리
sqlite3.o: sqlite3.c sqlite3.h
	$(CC) $(CFLAGS) -c sqlite3.c

# 정리 (컴파일된 파일 삭제)
clean:
	rm -f *.o $(TARGET)

# 초기화 (DB 파일까지 삭제하고 싶을 때 사용: make reset)
reset: clean
	rm -f game.db
