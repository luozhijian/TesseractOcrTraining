# -*- coding: utf-8 -*-

from scripts import tabledef
from scripts import forms
from scripts import helpers
from flask import Flask, redirect, url_for, render_template, request, session
import json
import sys
import os

app = Flask(__name__)
app.secret_key = os.urandom(12)  # Generic key for dev purposes only

 
#  most code is from Flaskex
# ======== Routing =  #
# -------- Login ----- #
@app.route('/', methods=['GET', 'POST'])
def login():
    if not session.get('logged_in'):
        form = forms.LoginForm(request.form)
        if request.method == 'POST':
            username = request.form['username'].lower()
            password = request.form['password']
            if form.validate():
                if helpers.credentials_valid(username, password):
                    session['logged_in'] = True
                    session['username'] = username
                    return json.dumps({'status': 'Login successful'})
                return json.dumps({'status': 'Invalid user/pass'})
            return json.dumps({'status': 'Both fields required'})
        return render_template('login.html', form=form)
    user = helpers.get_user()
    return render_template('home.html', user=user)


@app.route("/logout")
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'))


# -------- Signup ---------------------------------------------------------- #
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if not session.get('logged_in'):
        form = forms.LoginForm(request.form)
        if request.method == 'POST':
            username = request.form['username'].lower()
            password = helpers.hash_password(request.form['password'])
            email = request.form['email']
            if form.validate():
                if not helpers.username_taken(username):
                    helpers.add_user(username, password, email)
                    session['logged_in'] = True
                    session['username'] = username
                    return json.dumps({'status': 'Signup successful'})
                return json.dumps({'status': 'Username taken'})
            return json.dumps({'status': 'User/Pass required'})
        return render_template('login.html', form=form)
    return redirect(url_for('login'))


# -------- Settings ---------------------------------------------------------- #
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if session.get('logged_in'):
        if request.method == 'POST':
            password = request.form['password']
            if password != "":
                password = helpers.hash_password(password)
            email = request.form['email']
            helpers.change_user(password=password, email=email)
            return json.dumps({'status': 'Saved'})
        user = helpers.get_user()
        return render_template('settings.html', user=user)
    return redirect(url_for('login'))

# -------- images --------------- #
@app.route('/images', methods=['GET', 'POST'])
def images():
    if session.get('logged_in'):
        user = helpers.get_user()
        # list, get bitmap and linked text file
        filepairs = helpers.list_folder_image_text_pair(user.username )
        return render_template('images.html', user=user, filepairs = filepairs)
    return redirect(url_for('login'))

# -------- images --------------- #
@app.route('/results', methods=['GET', 'POST'])
def results():
    if session.get('logged_in'):
        user = helpers.get_user()
        # list the content in result folder, and for download
        results = helpers.list_folder_result(user.username )
        return render_template('results.html', results=results)
    return redirect(url_for('login'))
    
    
# -------- upload image --------------- #
@app.route('/upload', methods=['POST'])
def results():
    if session.get('logged_in'):
        user = helpers.get_user()
        fileitem = request.form['filename']
         
        e = helpers.save_image_file(user.username, fileitem)
        return render_template('results.html', results=results)
    return redirect(url_for('login'))
    

# -------- training --------------- #
@app.route('/training', methods=['GET'])
def training():
    if session.get('logged_in'):
        user = helpers.get_user()
        start_templateS = helpers.get_all_template(user.username )
        return render_template('training.html', templateS=start_templateS)
    return redirect(url_for('login'))    



# -------- start_training --------------- #
@app.route('/start_training', methods=['POST'])
def start_training():
    if session.get('logged_in'):
        user = helpers.get_user()
        start_template = request.form['template']
         
        return render_template('training.html', start_template=start_template)
    return redirect(url_for('login'))    


# ======== Main ================================= #
if __name__ == "__main__":
    app.run(debug=True, use_reloader=True, host="0.0.0.0")
