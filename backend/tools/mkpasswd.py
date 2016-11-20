import bcrypt
from getpass import getpass

def get_hashed_password(plain_text_password):
    return bcrypt.hashpw(plain_text_password, bcrypt.gensalt())

def check_password(plain_text_password, hashed_password):
    return bcrypt.checkpw(plain_text_password, hashed_password)

def main():
    plain_password = getpass('enter password: ')
    print(get_hashed_password(plain_password))


if __name__ == '__main__':
    main()
