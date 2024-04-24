from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pymysql


app = Flask(__name__)
app.secret_key = 'apptesting'  
#app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)
app.config['SESSION_PERMANENT'] = False

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    pass

@login_manager.user_loader
def user_loader(email):
    conn = pymysql.connect(host='localhost', user='root', password='Jb162814', db='fsusnow')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
    userInfo = cursor.fetchone()
    if userInfo:
        user = User()
        user.id = email
        user.is_admin = userInfo[6]
        return user

#######################################################################
    
#Account pages
    
#######################################################################
@app.route('/')
@login_required
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')



        conn = pymysql.connect(host='localhost', user='root', password='Jb162814', db='fsusnow')
        cursor = conn.cursor()


        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()


        if user:
            return "Email already exists. Please log in. <a href="/">Go back to login </a>."
        
        cursor.execute('INSERT INTO fsusnow.users (first_name, last_name, email, password) VALUES (%s, %s, %s, %s)', (first_name, last_name, email, password))
        conn.commit()
        return redirect(url_for('login'))
    
    
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')


        conn = pymysql.connect(host='localhost', user='root', password='Jb162814', db='fsusnow')
        cursor = conn.cursor()


        cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
        user = cursor.fetchone()


        if user:
            user = User()
            user.id = email
            login_user(user)
            return redirect(url_for('home'))
        

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('login'))









#######################################################################

#User Trip Details

#######################################################################

#this page is loaded when the view upcoming trips button is clicked on the home page
#it displays all of the trips that are being offered
@app.route('/trips')
@login_required
def upcoming_trips():
    conn = pymysql.connect(host='localhost', user='root', password='Jb162814', db='fsusnow')
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT * FROM trips')  #change to only after current date
    trips = cursor.fetchall()

    return render_template('trips.html', trips=trips)

#this is where the user is taken when a they click view more on the /trips page
@app.route('/trip_details/<int:trip_id>')
@login_required
def trip_details(trip_id):
    conn = pymysql.connect(host='localhost', user='root', password='Jb162814', db='fsusnow')
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT * FROM trips WHERE id = %s', (trip_id,))
    trip = cursor.fetchone()

    cursor.execute('SELECT * FROM housing WHERE trip_id = %s', (trip_id,))
    trip['housing'] = cursor.fetchall()

    cursor.execute('SELECT * FROM trip_signups WHERE trip_id = %s AND email = %s', (trip_id, current_user.id))
    is_signed_up = cursor.fetchone() is not None

    return render_template('trip_details.html', trip=trip, is_signed_up = is_signed_up)


#when the user hits sign up, it sends that form to this route, and then adds them to the database
@app.route('/signuptrip', methods=['POST'])
@login_required
def signuptrip():
    trip_id = request.form.get('trip_id')
    housing_id = request.form.get('housing_id')
    email = current_user.id

    conn = pymysql.connect(host='localhost', user='root', password='Jb162814', db='fsusnow')
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute('SELECT * FROM trip_signups WHERE trip_id = %s AND email = %s', (trip_id, email))
    if cursor.fetchone() is not None:
        return 'You have already signed up for a housing option for this trip. <a href="/">Go back to home page</a>.'

    cursor.execute('SELECT capacity FROM housing WHERE id = %s', (housing_id,))
    capacity = cursor.fetchone()['capacity']

    if capacity > 0:
        cursor.execute('UPDATE housing SET capacity = capacity - 1 WHERE id = %s', (housing_id,))

        cursor.execute('INSERT INTO trip_signups (trip_id, housing_id, email) VALUES (%s, %s, %s)', (trip_id, housing_id, email))

        conn.commit()
        return 'You have successfully signed up for the trip! <a href="/">Go back to home page</a>.'
    else:
        return 'Sorry, this housing option is no longer available. <a href="/">Go back to home page</a>.'
    
#this is the route that is used when the user is already signed up for a trip and they would like to not go on the trip anymore
@app.route('/unsignuptrip', methods=['POST'])
@login_required
def unsignuptrip():
    trip_id = request.form.get('trip_id')
    email = current_user.id

    conn = pymysql.connect(host='localhost', user='root', password='Jb162814', db='fsusnow')
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute('SELECT housing_id FROM fsusnow.trip_signups WHERE trip_id = %s AND email = %s', (trip_id, email))
    housing_id = cursor.fetchone()['housing_id']
    print(housing_id)
    print(email)
    print(trip_id)
    cursor.execute('DELETE FROM trip_signups WHERE trip_id = %s AND email = %s', (trip_id, email))

    cursor.execute('UPDATE housing SET capacity = capacity + 1 WHERE id = %s', (housing_id, ))

    conn.commit()
    return redirect(url_for('trip_details', trip_id=trip_id))

#######################################################################

#Rentals

#######################################################################


@app.route('/rentals', methods=['GET', 'POST'])
@login_required
def rentals():
    #this code is used to set up the default values if the user previously set rentals
    conn = pymysql.connect(host='localhost', user='root', password='Jb162814', db='fsusnow')
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute('SELECT rental_id FROM users WHERE email = %s', (current_user.id,))
    rental_id = cursor.fetchone()['rental_id']

    if rental_id != -1:
        cursor.execute('SELECT * FROM equipment WHERE id = %s', (rental_id,))
        equipment = cursor.fetchone()
    else:
        equipment = None



    if request.method == 'POST':
        ski_boots = request.form.get('ski_boots') == 'on'
        skis = request.form.get('skis') == 'on'
        snowboard_boots = request.form.get('snowboard_boots') == 'on'
        snowboard = request.form.get('snowboard') == 'on'
        gloves = request.form.get('gloves') == 'on'
        helmet = request.form.get('helmet') == 'on'
        bibs = request.form.get('bibs') == 'on'
        jacket = request.form.get('jacket') == 'on'
        goggles = request.form.get('goggles') == 'on'
        shoe_size = int(request.form.get('shoe_size'))
        weight = float(request.form.get('weight'))
        feet = int(float(request.form.get('height_feet')))  
        inches = int(float(request.form.get('height_inches'))) 
        height = (feet * 12) + inches


        conn = pymysql.connect(host='localhost', user='root', password='Jb162814', db='fsusnow')
        cursor = conn.cursor()

        cursor.execute('SELECT rental_id FROM fsusnow.users WHERE email = %s', (current_user.id,))
        rental_id = cursor.fetchone()[0]

        if rental_id == -1:
            cursor.execute('INSERT INTO fsusnow.equipment (ski_boots, skis, snowboard_boots, snowboard, gloves, helmet, bibs, jacket, shoe_size, goggles, weight, height) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', (ski_boots, skis, snowboard_boots, snowboard, gloves, helmet, bibs, jacket, shoe_size, goggles, weight, height))
            rental_id = cursor.lastrowid
            cursor.execute('UPDATE fsusnow.users SET rental_id = %s WHERE email = %s', (rental_id, current_user.id))
        else:
            cursor.execute('UPDATE fsusnow.equipment SET ski_boots = %s, skis = %s, snowboard_boots = %s, snowboard = %s, gloves = %s, helmet = %s, bibs = %s, jacket = %s, shoe_size = %s, goggles = %s, weight = %s, height = %s WHERE id = %s', (ski_boots, skis, snowboard_boots, snowboard, gloves, helmet, bibs, jacket, shoe_size, goggles, weight, height, rental_id))
        conn.commit()
        return redirect(url_for('home'))
    

    return render_template('rentals.html' , equipment = equipment)


#######################################################################

#Admin sites

#######################################################################


#admin home page
@app.route('/admin')
@login_required
def admin():
    if current_user.is_admin:
        return render_template('admin.html')
    else:
        return redirect(url_for('home'))


#this page is used to add a trip
@app.route('/add_trip', methods=['GET', 'POST'])
@login_required
def add_trip():
    if current_user.is_admin == False:
        return redirect(url_for('home'))
    if request.method == 'POST':
        name = request.form.get('trip_name')
        start = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        location = request.form.get('location')
        conn = pymysql.connect(host='localhost', user='root', password='Jb162814', db='fsusnow')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO trips (name, start_date, end_date, location) VALUES (%s, %s, %s, %s)', (name, start, end, location))
        conn.commit()
        return redirect(url_for('admin'))
    return render_template('add_trip.html')


#this page is used to view the trips
@app.route('/admin/trips')
@login_required
def admin_trips():
    if current_user.is_admin == False:
        return redirect(url_for('home'))
    conn = pymysql.connect(host='localhost', user='root', password='Jb162814', db='fsusnow')
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT * FROM trips')
    trips = cursor.fetchall()

    return render_template('admin_trips.html', trips=trips)


#this page is used to view stats on the trip from admin side, which is gotten to from the view info on the /admin/trips page
@app.route('/admin/trip_details/<int:tripId>')
@login_required
def admin_trip_details(tripId):
    if current_user.is_admin == False:
        return redirect(url_for('home'))
    conn = pymysql.connect(host='localhost', user='root', password='Jb162814', db='fsusnow')
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute('SELECT * FROM trips WHERE id = %s', (tripId,))
    trip = cursor.fetchone()

    cursor.execute('SELECT * FROM trip_signups WHERE trip_id = %s ORDER BY housing_id', (tripId,))
    signups = cursor.fetchall()

    for signup in signups:
        cursor.execute('SELECT * FROM housing WHERE id = %s', (signup['housing_id'],))
        signup['housing'] = cursor.fetchone()
        cursor.execute('SELECT first_name, last_name FROM users WHERE email = %s', (signup['email'],))
        user = cursor.fetchone()
        signup['name'] = user['first_name'] + ' ' + user['last_name']


    cursor.execute('''
        SELECT SUM(equipment.ski_boots) AS total_ski_boots, 
               SUM(equipment.skis) AS total_skis, 
               SUM(equipment.snowboard_boots) AS total_snowboard_boots, 
               SUM(equipment.snowboard) AS total_snowboard, 
               SUM(equipment.gloves) AS total_gloves, 
               SUM(equipment.helmet) AS total_helmet, 
               SUM(equipment.bibs) AS total_bibs, 
               SUM(equipment.jacket) AS total_jacket, 
               SUM(equipment.goggles) AS total_goggles 
        FROM equipment 
        INNER JOIN users ON equipment.id = users.rental_id 
        INNER JOIN trip_signups ON users.email = trip_signups.email 
        WHERE trip_signups.trip_id = %s
    ''', (tripId,))
    equipment_totals = cursor.fetchone()
    return render_template('admin_trip_details.html', trip=trip, signups=signups, equipment_totals=equipment_totals)

#this is used to add housing options to the trips
@app.route('/add_housing', methods=['GET', 'POST'])
@login_required
def add_housing():
    if current_user.is_admin == False:
        return redirect(url_for('home'))
    conn = pymysql.connect(host='localhost', user='root', password='Jb162814', db='fsusnow')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM trips')
    trips = cursor.fetchall()
    if request.method == 'POST':
        streetAddress = request.form.get('streetAddress')
        town = request.form.get('town')
        state = request.form.get('state')
        zipCode = request.form.get('zipCode')
        price = float(request.form.get('price'))
        capacity = int(request.form.get('capacity'))
        tripId = int(request.form.get('tripId'))
        name = request.form.get('Name')
        cursor.execute('INSERT INTO housing (street_address, town, state, zip_code, price, capacity, trip_id, name) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', (streetAddress, town, state, zipCode, price, capacity, tripId, name))
        conn.commit()
        return redirect(url_for('admin'))
    return render_template('add_housing.html', trips=trips)




#######################################################################

#Advanced function

#######################################################################

@app.route('/adv')
def adv():
    return render_template('advancedfunction.html')

@app.route('/advresults', methods=['POST'])
def advresults():
    min_days = request.form['min_days']
    blackout_start_dates = request.form.getlist('blackout_start_dates[]')
    blackout_end_dates = request.form.getlist('blackout_end_dates[]')
    budget = request.form['budget']
    maxski_days = request.form['max_days']
    blackout_periods = zip(blackout_start_dates, blackout_end_dates)

    conn = pymysql.connect(host='localhost', user='root', password='Jb162814', db='fsusnow')
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    query = '''
    SELECT trips.id
    FROM trips
    JOIN housing ON trips.id = housing.trip_id
    WHERE housing.price <= %s
    '''

    # Add blackout dates
    for start, end in blackout_periods:
        query += ' AND (fsusnow.trips.start_date NOT BETWEEN \''+ start + '\' AND \''+ end + '\' OR fsusnow.trips.end_date NOT BETWEEN \''+ start + '\' AND \''+ end + '\')'
    cursor.execute(query, (budget,))
    matching_trips_dates = cursor.fetchall()
    trips = [trip.get('id') for trip in matching_trips_dates]
    trips = list(set(trips))
    matching_trips = []
    for i in trips:
        cursor.execute('SELECT trip_id,min(price) as MinPrice FROM housing GROUP BY trip_id HAVING trip_id = %s' , (i,))
        matching_trips.append(cursor.fetchall()[0])
    for trips in matching_trips:
        cursor.execute('SELECT DATEDIFF(trips.end_date,trips.start_date) as trip_duration from trips WHERE trips.id = %s' ,(trips.get('trip_id'),))
        trips['trip_duration'] = cursor.fetchone()['trip_duration']

    
    for trips in matching_trips:
        trips['MinPrice'] = float(trips['MinPrice'])
        
    matching_trips_list = [(trips['trip_duration'],trips['MinPrice'],trips['trip_id']) for trips in matching_trips]
    maxski_days = int(maxski_days)
    min_days = int(min_days)
    budget = float(budget)
    trips1 = dp_optimize_trips(matching_trips_list,min_days,maxski_days,budget)
    max_days = 0
    total_price = 0
    for trip in trips1:
        max_days += trip[0]
        total_price += trip[1]

    trips = []
    for id in trips1:
        tripID = id[2]
        cursor.execute("SELECT start_date, end_date, name FROM trips WHERE id = %s",(id[2],))
        cur = cursor.fetchone()
        startDate = cur['start_date']
        endDate = cur['end_date']
        name = cur['name']
        for t in matching_trips_list:
            if t[2] == tripID:
                trip = t
        cursor.execute("SELECT name FROM fsusnow.housing WHERE trip_id = %s AND price = %s", (tripID,id[1]))
        nameHousing = cursor.fetchone()['name']
        trips.append({'start_date': startDate, 'end_date': endDate,'num_days': trip[0],
                      'name': name, 'price':trip[1], 'housing': nameHousing})
    
    return render_template('advancedresults.html', max_days = max_days, total_price = total_price, trips = trips)

def dp_optimize_trips(trips, min_days, max_days, budget):
    dp = {0.0: (0, [])}

    for trip in trips:
        duration, cost, trip_id = trip
        current_entries = sorted(dp.items(), reverse=True)  
        for current_budget, (current_duration, current_trips) in current_entries:
            new_budget = current_budget + cost
            new_duration = current_duration + duration
            if new_duration <= max_days and new_budget <= budget:
                if new_budget not in dp or new_duration > dp[new_budget][0]:
                    dp[new_budget] = (new_duration, current_trips + [trip])

    best_combination = []
    max_duration = 0
    for total_cost, (total_duration, trips) in dp.items():
        if min_days <= total_duration <= max_days and total_duration > max_duration:
            best_combination = trips
            max_duration = total_duration

    return best_combination


if __name__ == "__main__":
    app.run(debug=True)