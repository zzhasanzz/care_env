import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "1234"
    DB_NAME = "care_env"

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
