#!/usr/bin/env python2.7

# Alec Silverstein and Richard Moessner
# ags2179 and rmm2233
# W4111 Intro to Databases Project 1 Part 3
# server.py - server source code that communicates with html templates
# Run with "python server.py", go to "http://<IP>:8111 in browser

# ******************** INITIAL SETUP ********************

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response

globalName = ""

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

app.debug = True

DATABASEURI = "postgresql://ags2179:CWPKVH@w4111db.eastus.cloudapp.azure.com/ags2179"

# Create database engine
engine = create_engine(DATABASEURI)


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None


@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


# ******************** MAIN PAGE ********************


@app.route('/')
def index():
  cursor = g.conn.execute('SELECT username FROM users')
  names = []
  for result in cursor:
    names.append(result['username'])
  cursor.close()

  context = dict(data = names)

  return render_template("index.html", **context)


@app.route('/addUser', methods=['POST', 'GET'])
def addUser():
  global globalName
  name = request.form['name']
  if name == "":
    return redirect('/')
  globalName = name
  try:
    g.conn.execute('INSERT INTO users VALUES (%s, 0)', globalName)
  except:
    return "User already exists - please go back and retry"
  g.conn.execute('INSERT INTO has_cart VALUES (%s, 1, 0, 0)', globalName)
  return redirect('/')


# ******************** CART SECTION ********************


@app.route('/cart')
def cart():
  return render_template("cart.html")


@app.route('/getCart', methods=['POST', 'GET'])
def getCart():
  global globalName
  try:
    name = request.form['name']
  except:
    return redirect('/cart')
  globalName = name
  
  nameCursor = g.conn.execute('SELECT DISTINCT username FROM users')
  names = []
  for result in nameCursor:
    names.append(result[0])
  if globalName not in names:
    return "Invalid entry - please go back and retry"
  
  cursor = g.conn.execute('SELECT DISTINCT c.gamename, g.price FROM contains c, games_madeby g WHERE c.gamename = g.gamename AND c.username = %s', globalName)
  cursor2 = g.conn.execute('SELECT DISTINCT totalcost FROM has_cart WHERE username = %s', globalName)
  
  cost = []
  for result in cursor2:
    cost.append(result)
  try:
    total = cost[0][0]
  except:
    total = 0
  cursor2.close()  

  cart = []
  for result in cursor:
    cart.append(result)
  cursor.close()

  context = cart

  return render_template("showcart.html", data = context, total = total)


@app.route('/addToCart', methods=['POST', 'GET'])
def addToCart():
  global globalName
  name = request.form['name']
  try:
    g.conn.execute('INSERT INTO contains VALUES (%s, 1, %s)', globalName, name)
  except:
    return "Invalid entry - please go back and retry"
  cursor = g.conn.execute('SELECT DISTINCT price FROM games_madeby WHERE gamename = %s', name)
  cost = []
  for result in cursor:
    cost.append(result)
  addPrice = cost[0][0]
  
  cursor2 = g.conn.execute('SELECT DISTINCT totalcost FROM has_cart WHERE username = %s', globalName)

  cost = []
  for result in cursor2:
    cost.append(result)
  total = cost[0][0]
  cursor2.close()

  total = total + addPrice

  args = (total, globalName)

  g.conn.execute('UPDATE has_cart SET totalcost = %s WHERE username = %s', args)
  g.conn.execute('UPDATE has_cart SET numgames = numgames + 1 WHERE username = %s', globalName)
  cursor.close()

  cursor2 = g.conn.execute('SELECT DISTINCT c.gamename, g.price FROM contains c, games_madeby g WHERE c.gamename = g.gamename AND c.username = %s', globalName)

  cart = []
  for result in cursor2:
    cart.append(result)
  cursor2.close()

  context = cart

  return render_template("showcart.html", data = context, total = total)


# ******************** GAME SECTION ********************

@app.route('/games')
def games():
  cursor = g.conn.execute('SELECT DISTINCT * FROM games_madeby')
  games = []
  for result in cursor:
    games.append(result)
  cursor.close()

  context = games

  return render_template("games.html", data = context)


@app.route('/games', methods=['POST'])
def gameSearch():

  devs = []
  consoles = []
  price = 60.00

  for n in request.form:
    if n == "ksubmit":
      continue
    elif n.find("dev") >= 0:
      devs.append(request.form[n])
    elif n.find("con") >= 0:
      consoles.append(request.form[n])
    elif n == "Price" and request.form[n] != "NA":
      price = float(request.form[n])

  if not devs and not consoles and price == 60.00:
    return redirect('/games')

  condition = ""
  devCondition = ""
  conCondition = ""
  priCondition = ""
 
  if devs:
    for n in range(0, len(devs) - 1):
      devCondition = devCondition + "devname = \'" + devs[n] + "\'" + " OR "
    devCondition = devCondition + "devname = \'" + devs[len(devs) - 1] + "\'"

  if consoles:
    for n in range(0, len(consoles) - 1):
      conCondition = conCondition + "consolename = \'" + consoles[n] + "\'" + " OR "
    conCondition = conCondition + "consolename = \'" + consoles[len(consoles) - 1] + "\'"

  if price < 60:
    priCondition = priCondition + "price <= " + str(price) 

  if devCondition != "" and conCondition != "" and priCondition != "":
    condition = condition + "(" + devCondition + ")" + " AND " + "(" + conCondition + ")"+ " AND " + "(" + priCondition + ")"
    query = "SELECT DISTINCT g.gamename, g.devname, g.price, g.releasedate, g.esrbrating, g.ignrating FROM games_madeby g, runs_on r WHERE (g.gamename = r.gamename) AND (" + condition + ")"
  elif devCondition != "" and conCondition != "":
    condition = condition + "(" + devCondition + ")" + " AND " + "(" + conCondition + ")"
    query = "SELECT DISTINCT g.gamename, g.devname, g.price, g.releasedate, g.esrbrating, g.ignrating FROM games_madeby g, runs_on r WHERE (g.gamename = r.gamename) AND (" + condition + ")"
  elif devCondition != "" and priCondition != "":
    condition = condition + "(" + devCondition + ")" + " AND " + "(" + priCondition + ")"
    query = "SELECT DISTINCT * FROM games_madeby WHERE (" + condition + ")"
  elif conCondition != "" and priCondition != "":
    condition = condition + "(" + conCondition + ")" + " AND " + "(" + priCondition + ")"
    query = "SELECT DISTINCT g.gamename, g.devname, g.price, g.releasedate, g.esrbrating, g.ignrating FROM games_madeby g, runs_on r WHERE (g.gamename = r.gamename) AND (" + condition + ")"
  elif devCondition != "":
    condition = condition + "(" + devCondition + ")"
    query = "SELECT DISTINCT * FROM games_madeby WHERE (" + condition + ")"
  elif conCondition != "":
    condition = condition + "(" + conCondition + ")"
    query = "SELECT DISTINCT g.gamename, g.devname, g.price, g.releasedate, g.esrbrating, g.ignrating FROM games_madeby g, runs_on r WHERE (g.gamename = r.gamename) AND (" + condition + ")"
  elif priCondition != "":
    condition = condition + "(" + priCondition + ")"
    query = "SELECT DISTINCT * FROM games_madeby WHERE (" + condition + ")"
  else:
    condition = ""
    query = "SELECT DISTINCT * FROM games_madeby WHERE (" + condition + ")"

  # In this case there is no worry of SQL injection because user only has access to check boxes  
  cursor = g.conn.execute(query)

  games = []
  for result in cursor:
    games.append(result)
  cursor.close()

  context = games

  return render_template("games.html", data = context)


# ******************** FAVORITED SECTION ********************

@app.route('/favorited')
def favorited():
  return render_template("favorited.html")

@app.route('/getFavorited', methods=['POST', 'GET'])
def getFavorited():
  global globalName
  try:
    name = request.form['name']
  except:
    return redirect('/favorited')
  globalName = name

  nameCursor = g.conn.execute('SELECT DISTINCT username FROM users')
  names = []
  for result in nameCursor:
    names.append(result[0])
  if globalName not in names:
    return "Invalid entry - please go back and retry"

  cursor = g.conn.execute('SELECT DISTINCT f.gamename, g.ignrating FROM favorited f, games_madeby g WHERE f.gamename = g.gamename AND f.username = %s', globalName)

  favorited = []
  for result in cursor:
    favorited.append(result)
  cursor.close()

  context = favorited

  average = 0

  if favorited:
    cursor2 = g.conn.execute('SELECT AVG(g.ignrating) FROM favorited f, games_madeby g WHERE f.gamename = g.gamename AND f.username = %s', globalName)

    avg = []
    for result in cursor2:
      avg.append(result)
    cursor2.close()

    average = avg[0][0]

    average = round(average, 2)

  return render_template("showfavorited.html", data = context, average = average)


@app.route('/addToFavorited', methods=['POST', 'GET'])
def addToFavorited():
  global globalName
  name = request.form['name']
  try:
    g.conn.execute('INSERT INTO favorited VALUES (%s, %s)', globalName, name)
  except:
    return "Invalid entry - please go back and retry"

  g.conn.execute('UPDATE users SET numgames = numgames + 1 WHERE username = %s', globalName)

  cursor = g.conn.execute('SELECT DISTINCT f.gamename, g.ignrating FROM favorited f, games_madeby g WHERE f.gamename = g.gamename AND f.username = %s', globalName)

  favorited = []
  for result in cursor:
    favorited.append(result)
  cursor.close()

  context = favorited

  cursor2 = g.conn.execute('SELECT AVG(g.ignrating) FROM favorited f, games_madeby g WHERE f.gamename = g.gamename AND f.username = %s', globalName)

  avg = []
  for result in cursor2:
    avg.append(result)
  cursor2.close()

  average = avg[0][0]
  
  average = round(average, 2)

  return render_template("showfavorited.html", data = context, average = average)


# ******************** FOLLOWED SECTION ********************

@app.route('/followed')
def followed():
  return render_template("followed.html")

@app.route('/getFollowed', methods=['POST', 'GET'])
def getFollowed():
  global globalName
  try:
    name = request.form['name']
  except:
    return redirect('/followed')
  globalName = name

  nameCursor = g.conn.execute('SELECT DISTINCT username FROM users')
  names = []
  for result in nameCursor:
    names.append(result[0])
  if globalName not in names:
    return "Invalid entry - please go back and retry"

  cursor = g.conn.execute('SELECT DISTINCT d.devname, d.headquarters FROM follows f, developers d WHERE f.devname = d.devname AND f.username = %s', globalName)

  followed = []
  for result in cursor:
    followed.append(result)
  cursor.close()

  context = followed

  return render_template("showfollowed.html", data = context)


@app.route('/addToFollowed', methods=['POST', 'GET'])
def addToFollowed():
  global globalName
  name = request.form['name']
  try:
    g.conn.execute('INSERT INTO follows VALUES (%s, %s)', globalName, name)
  except:
    return "Invalid entry - please go back and retry"

  cursor = g.conn.execute('SELECT DISTINCT d.devname, d.headquarters FROM follows f, developers d WHERE f.devname = d.devname AND f.username = %s', globalName)

  followed = []
  for result in cursor:
    followed.append(result)
  cursor.close()

  context = followed

  return render_template("showfollowed.html", data = context)


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
