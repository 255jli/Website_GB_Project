import sqlite3

DB = 'users.db'

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    print('Tables:')
    for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        print(' -', row[0])

    print('\nUsers:')
    try:
        for row in cur.execute('SELECT login, created_at FROM users'):
            print(' -', row)
    except Exception as e:
        print(' users table error:', e)

    conn.close()

if __name__ == '__main__':
    main()
