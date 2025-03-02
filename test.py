import MySQLdb

db = MySQLdb.connect(
    host="localhost",
    user="root",
    passwd="1234",
    database="care_env"
)

mycursor = db.cursor()

# first commit 
