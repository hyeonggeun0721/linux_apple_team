CC = gcc
CFLAGS = -Wall -g
TARGET = server
# sqlite3.o 를 추가하여 같이 컴파일
OBJS = main.o network.o game_logic.o database.o sqlite3.o 

all: $(TARGET)

$(TARGET): $(OBJS)
	# -lsqlite3 제거 -> sqlite3.o가 대신함
	# -lpthread -ldl 추가 (SQLite가 내부적으로 사용함)
	$(CC) $(CFLAGS) -o $@ $^ -lpthread -ldl 

clean:
	rm -f $(OBJS) $(TARGET) game.db