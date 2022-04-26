from flask import Flask, render_template, flash, redirect, url_for, session, request, logging, abort, jsonify

from flask_mysqldb import MySQL

from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from functools import update_wrapper
from io import BytesIO
import io
import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import numpy as np
import pymysql
import matplotlib.pyplot as plt
import pandas as pd
plt.style.use('ggplot')
import pygal
import json

from urllib.request import urlopen 

from flask import Flask, render_template
from pygal.style import DarkSolarizedStyle

app = Flask(__name__)


# Configuration de la base de donnees MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'ismail'
app.config['MYSQL_PASSWORD'] = 'yes'
app.config['MYSQL_DB'] = 'art'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['SECRET_KEY']='secret123'
# initialisation MYSQL
mysql = MySQL(app)


@app.route('/')
def index():
    return render_template('home.html')




data=json.loads(open('/home/ismedo/Documents/csvjson.json').read())
columns = [
  {
    "field": "Time","title": "date", "sortable": True,
  },{"field": "AirTemp(deg C)","title": "Temp_air(deg C)","sortable": True,},{"field": "Humidity (%)",
    "title": "humidité (%)","sortable": True,},{"field": "WindSpd (m.s-1)","title": "vitesse vent (m.s-1)","sortable": True,},
  {"field": "Radiation (W.m- )","title": "Radiation solaire(W.m- )","sortable": True,}
]

@app.route('/table')
def table():
    return render_template("table.html",
      data=data,
      columns=columns,
      title='Mesure des données Agro météorologiques')



@app.route('/Station')

def Station():

    cur = mysql.connection.cursor()


    result = cur.execute("SELECT * FROM Station")

    Station = cur.fetchall()

    if result > 0:
        return render_template('Station.html', Station=Station)
    else:
        msg = 'No Station Found'
        return render_template('Station.html', msg=msg)

    cur.close()
@app.route('/graph')
def pygalexample():

    graph = pygal.Line()

    graph.x_labels = [i for i in range(1,5)]
    graph.add('Temp_Max',  [15, 31, 89, 200, 356, 900])
    graph.add('Temp_moy',    [15, 45, 76, 80,  91,  95])
    graph.add('Temp_min',     [5,  51, 54, 102, 150, 201])

    graph_data = graph.render_data_uri()
    return render_template("graph.html", graph_data = graph_data)


@app.route("/charti")
def load_index():
	return render_template('indexi.html')

@app.route("/chart")
def chart():

	month = request.args.get('month')


	file = open("toronto_historical.csv")
	file_contents = file.readlines()
	toronto_info = file_contents[1847:1981]
	for i in range(len(toronto_info)):
		toronto_info[i] = toronto_info[i].split(",")
		for j in range(len(toronto_info[i])):
			toronto_info[i][j] = toronto_info[i][j].strip('"')
			print(toronto_info[i])


	x_labels = []
	high_temps = []
	low_temps = []
	mean_temps= []

	for i in range(len(toronto_info)):
		if int(toronto_info[i][2]) == 6 or int(toronto_info[i][2]) == 7 or int(toronto_info[i][2]) == 7 :	# January -- > In the future use a bool array as a mask to filter out which months to show (for yearly trends)
			x_labels.append(toronto_info[i][0])
			high_temps.append(toronto_info[i][3])
			low_temps.append(toronto_info[i][5])
			mean_temps.append(toronto_info[i][7])

	print(month)


	return jsonify (
		name = "temperature mesuree par notre station agrometeo",
		mean_temp = mean_temps,
		high_temp = high_temps,
		low_temp = low_temps,
		labels = x_labels
	)



@app.route('/stat/<string:id>/')

def stat(id):

    cur = mysql.connection.cursor()


    result = cur.execute("SELECT * FROM Station WHERE id = %s", [id])

    stat = cur.fetchone()

    return render_template('stat.html', stat=stat)


# classe s'inscrire
class RegisterForm(Form):
    name = StringField('Nom', [validators.Length(min=1, max=50)])
    username = StringField('Nom d utilisation ', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Mot de passe', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


# User Register
@app.route('/register', methods=['GET', 'POST'])

def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))


        cur = mysql.connection.cursor()


        cur.execute("INSERT INTO Personne(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))


        mysql.connection.commit()


        cur.close()

        flash('Vous êtes maintenant inscrit sur MetAgro et vous pouvez vous connecter', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)


# login membre
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        username = request.form['username']
        password_candidate = request.form['password']


        cur = mysql.connection.cursor()


        result = cur.execute("SELECT * FROM Personne WHERE username = %s", [username])

        if result > 0:

            data = cur.fetchone()
            password = data['password']

            # commparer les passwords chiffres
            if sha256_crypt.verify(password_candidate, password):

                session['logged_in'] = True
                session['username'] = username

                flash('vous êtes maintenant connceté sur MetAgro', 'success')

                return redirect(url_for('Stations'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)

            cur.close()
        else:
            error = 'Nom d utilisateur non trouvé'
            return render_template('login.html', error=error)

    return render_template('login.html')


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):

        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:

            flash('non autorise, svp connectez vous', 'danger')
            return redirect(url_for('login'))
    return wrap



# deconnecter
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('connectez vous a nouveau', 'success')
    return redirect(url_for('login'))

@app.route('/about')
@is_logged_in
def about():
    return render_template('about.html')

# Stations
@app.route('/Stations')
@is_logged_in
def Stations():

    cur = mysql.connection.cursor()


    result = cur.execute("SELECT * FROM Station WHERE Localisation = %s", [session['username']])

    Station = cur.fetchall()

    if result > 0:
        return render_template('Stations.html', Station=Station)
    else:
        msg = 'No Station Found'
        return render_template('Stations.html', msg=msg)
    # fermer lq connextion avec la base de donnees
    cur.close()

# stat Form Class
class StatForm(Form):
    Nom = StringField('Nom', [validators.Length(min=1, max=200)])
    Description = TextAreaField('Description', [validators.Length(min=30)])


# Add Stat
@app.route('/add_station', methods=['GET', 'POST'])
@is_logged_in
def add_station():
    form = StatForm(request.form)
    if request.method == 'POST' and form.validate():
        Nom = form.Nom.data
        Description = form.Description.data

        # creer le curseur de connexion avec la bdd
        cur = mysql.connection.cursor()


        cur.execute("INSERT INTO Station(Nom, Description, Localisation) VALUES(%s, %s, %s)",(Nom, Description, session['username']))

        # enregister dans bdd
        mysql.connection.commit()

        #fermer la cnx
        cur.close()

        flash('Station Created', 'success')

        return redirect(url_for('Stations'))

    return render_template('add_station.html', form=form)


# Modifier la station
@app.route('/modifier_station/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def modifier_station(id):

    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM Station WHERE id = %s", [id])

    stat = cur.fetchone()
    cur.close()

    form = StatForm(request.form)


    form.Nom.data = stat['Nom']
    form.Description.data = stat['Description']

    if request.method == 'POST' and form.validate():
        Nom = request.form['Nom']
        Description = request.form['Description']


        cur = mysql.connection.cursor()
        app.logger.info(Nom)

        cur.execute ("UPDATE Station SET Nom=%s, Description=%s WHERE id=%s",(Nom, Description, id))

        mysql.connection.commit()


        cur.close()

        flash('stat Updated', 'success')

        return redirect(url_for('Stations'))

    return render_template('modifier_station.html', form=form)


@app.route('/delete_stat/<string:id>', methods=['POST'])
@is_logged_in
def delete_stat(id):

    cur = mysql.connection.cursor()


    cur.execute("DELETE FROM Station WHERE id = %s", [id])


    mysql.connection.commit()


    cur.close()

    flash('stat Deleted', 'success')

    return redirect(url_for('Stations'))

if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)
