from flask import Flask, render_template, request, session
import sqlite3
import duckdb
from datetime import datetime

app = Flask(__name__)
app.secret_key = 't35t1'

#need to figure out how to get ip address data and how to use rememberme checkbox

############ MAIN/LOGIN PAGE ###########

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    if request.method == 'POST':
        signup_datetime = datetime.now()
        signup_first_name = request.form['first_name']
        signup_last_name = request.form['last_name']
        # signup_city = request.form['city']
        # signup_state = request.form['state'] don't forget to add this back in sql query
        signup_email = request.form['email']
        signup_password = request.form['password']
        #signup_rememberme  = request.form['rememberme']
        signup_ip = request.remote_addr

        neighborhostdb = duckdb.connect('neighborhost.db')
        neighborsdf = neighborhostdb.sql("SELECT email FROM neighbors").df()
        email = neighborsdf['email'].tolist()

        if signup_email in email:
            return "Looks like there's already an account with this email."
        else:
            conn = sqlite3.connect('neighborhost.db')
            cursor = conn.cursor()
            cursor.execute("""INSERT INTO neighbors (neighbor_id, datetime, first_name, last_name, email, password)
                            VALUES (((SELECT MAX(neighbor_id) FROM neighbors)+1), ?, ?, ?, ?, ?)""", 
                            (signup_datetime, signup_first_name, signup_last_name, signup_email, signup_password))
            conn.commit()
            conn.close()

            neighborhostdb = duckdb.connect('neighborhost.db')
            neighborsdf = neighborhostdb.sql("SELECT MAX(neighbor_id) AS neighbor_id FROM neighbors").df()
            signup_neighbor_id = neighborsdf['neighbor_id'].tolist()

            conn = sqlite3.connect('neighborhost.db')
            cursor = conn.cursor()
            cursor.execute("""INSERT INTO logins (login_id, neighbor_id, datetime, ip)
                           VALUES (((SELECT MAX(login_id) AS login_id FROM logins)+1), ?, ?, ?)""",
                           (sum(signup_neighbor_id), signup_datetime, signup_ip))
            conn.commit()
            conn.close()

            session['signup_data'] = {
                'neighbor_id' : signup_neighbor_id,
                'datetime' : signup_datetime,
                'first_name' : signup_first_name,
                'last_name' : signup_last_name,
                'email' : signup_email,
                'password' : signup_password,
                'ip' : signup_ip
            }

            ######## VERIFICATION PAGE #########
                
            return render_template('setup.html')
        
@app.route('/setup', methods=['POST'])
def setup():
    signup_data = session.get('signup_data', {})
    neighbor_id = sum(signup_data.get('neighbor_id'))
    email = signup_data.get('email')
    password = signup_data.get('password')

    if request.method == 'POST':
        setup_address = request.form['address']

        conn = sqlite3.connect('neighborhost.db')
        cursor = conn.cursor()
        cursor.execute("""UPDATE neighbors
                       SET address = ?
                       WHERE neighbor_id = ? AND email = ? AND password = ?""", (setup_address, neighbor_id, email, password))
        conn.commit()
        conn.close()

        session.pop('signup_data', None)

        ############# LANDING PAGE #############
        
        return render_template('logged_in.html')

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        login_email = request.form['email']
        login_password = request.form['password']
        login_datetime = datetime.now()
        login_ip = request.remote_addr #need to make it if ip address is different but email and password are correct, need to flag
        login_info = login_email + " " + login_password
        login_info_w_ip = login_email +  " " + login_password + " " + login_ip

        conn = sqlite3.connect('neighborhost.db')
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO logins (login_id, neighbor_id, datetime, ip)
                       VALUES (((SELECT MAX(login_id) FROM logins)+1),
                       (SELECT neighbor_id FROM neighbors WHERE email = ? AND password = ?), 
                       ?, 
                       (SELECT l.ip FROM logins l 
                       JOIN neighbors n ON n.neighbor_id AND l.neighbor_id 
                       WHERE l.neighbor_id = (SELECT neighbor_id FROM neighbors WHERE email = ? AND password = ?)))""", 
                       (login_email, login_password, login_datetime, login_email, login_password))
        conn.commit()
        conn.close() #need to add a session thing that carries over login info to event_plan action

        neighborhostdb = duckdb.connect('neighborhost.db')
        logins = neighborhostdb.sql("""SELECT CONCAT(email, ' ', password) AS login FROM neighbors""").df()['login'].tolist()
        logins_w_ip = neighborhostdb.sql("""SELECT CONCAT(n.email, ' ',  n.password, ' ', l.ip) AS login_w_ip FROM neighbors n
                                         JOIN logins l ON l.neighbor_id = n.neighbor_id""").df()['login_w_ip'].tolist()

        if login_info in logins:
            if login_info_w_ip in logins_w_ip:

                #add session login data to be fetched here

                ############# LANDING PAGE #############

                return render_template('logged_in.html')
            elif login_info in logins:
                if login_info_w_ip not in logins_w_ip:

                    ######### IP VERIFICATION PAGE #########               

                    return render_template('ip_verif.html')
        else:
            return 'We could not find an account with this email and/or password.'
    else: 
        return 'We could not find an account with this email and/or password.'

#@app.route('/ip_verif',methods=['POST']) need to add block of code to backend ip verification by emailing users - if ip is verified, that's when it's input

@app.route('/event_plan', methods=['POST'])
def event_plan():
    if request.method == 'POST':
        event_title = request.form['event_title']
        return render_template('events.html')
    
if __name__ == '__main__':
    app.run(debug=True)