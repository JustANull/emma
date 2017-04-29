import sqlite3 as sql

# Metadata
versionNumber = "2.0.0-Tech-3"

# Chrome
def show_emma_banner():
    print u"\n .ooooo.  ooo. .oo.  .oo.   ooo. .oo.  .oo.    .oooo.\nd88' \u006088b \u0060888P\"Y88bP\"Y88b  \u0060888P\"Y88bP\"Y88b  \u0060P  )88b\n888ooo888  888   888   888   888   888   888   .oP\"888\n888    .,  888   888   888   888   888   888  d8(  888\n\u0060Y8bod8P' o888o o888o o888o o888o o888o o888o \u0060Y888\"\"8o\n\n        EXPANDING MODEL of MAPPED ASSOCIATIONS\n                     Version " + versionNumber + "\n"

def show_database_stats():
    connection = sql.connect('emma.db')
    cursor = connection.cursor()

    with connection:
        cursor.execute("SELECT * FROM associationmodel")
        associationModelItems = "{:,d}".format(len(cursor.fetchall()))
        cursor.execute("SELECT * FROM dictionary")
        dictionaryItems = "{:,d}".format(len(cursor.fetchall()))
    print "Database contains %s associations for %s words." % (associationModelItems, dictionaryItems)

# Weird variables and lists
netspeak = {
    u'aight': [u'alright'],
    u'btw': [u'by', u'the', u'way'],
    u'cn': [u'can'],
    u'gonna': [u'going', u'to'],
    u'im': [u'I\'m'],
    u'imo': [u'in', u'my', u'opinion'],
    u'lemme': [u'let', u'me'],
    u'n': [u'and'],
    u'obv': [u'obviously'],
    u'omg': [u'oh', u'my', u'god'],
    u'r': [u'are'],
    u'tbh': [u'to', u'be', u'honest'],
    u'u': [u'you'],
    u'ur': [u'your'],
    u'yea': [u'yeah']
}