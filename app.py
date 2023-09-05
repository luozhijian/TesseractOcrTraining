# -*- coding: utf-8 -*-

from scripts import tabledef
from scripts import forms
from scripts import helpers
from flask import Flask, redirect, url_for, render_template, request, session, send_from_directory, Response
from pygtail import Pygtail
import json
import sys
import os
import time

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
                    # return results()
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
    
    
@app.route('/imagefiles/<name>')
def imagefiles(name):
    print('imagefile%s'%name)
    if session.get('logged_in'):
        username = helpers.get_username()
        return send_from_directory(helpers.generate_image_folder(username), name)
    return redirect(url_for('login'))
        
@app.route('/resultfiles/<name>')
def resultfiles(name):
    print('imagefile%s'%name)
    if session.get('logged_in'):
        username = helpers.get_username()
        return send_from_directory(helpers.generate_result_folder(username), name)
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
def upload():
    if session.get('logged_in'):
        user = helpers.get_user()
        
        files = request.files.getlist("fileupload")
        
        # fileitem = request.files['fileupload']
        for file in files:
            e = helpers.save_image_file(user.username, file)
            
        return images()

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
        start_template = request.form['templatename']
        helpers.start_training_process(user.username, start_template)
        return render_template('training_in_process.html', start_template=start_template)
    return redirect(url_for('login'))    


@app.route('/stream')
def stream():
 
    if session.get('logged_in'):
        username = helpers.get_username()
        def generate():
            logfilename= helpers.get_current_log_name(username)
            print (username  + '  ' + logfilename)
            
            if not logfilename :
                yield 'cannot find log file' + "\n\n" + "\n\n"
                yield 'close' + "\n\n" + "\n\n"
                return
            for line in Pygtail(logfilename ):
                print (line)
                yield "data:" + str(line)  + "\n\n" + "\n\n"
                time.sleep(0.1)
            yield 'close' + "\n\n" + "\n\n"

        return Response(generate(), mimetype= 'text/event-stream')
    return redirect(url_for('login'))    
    

@app.route('/imageedit', methods=['GET'])
def imageedit():
    if session.get('logged_in'):
        filename = request.args.get("file")
        user = helpers.get_user()
        #image_full_path_url = './files/' + user.username + '/' + filename
        image_full_path_url = filename
        #print(filename)
        current_text = helpers.read_image_text(user.username, filename)
        return render_template('imageedit.html', image_full_path=image_full_path_url
                , image_path=filename, current_text=current_text)
    return redirect(url_for('login'))    


@app.route('/savetext', methods=['GET', 'POST' ])
def savetext():
    if session.get('logged_in'):
        imagefilename = request.args.get("image")
        user = helpers.get_user()
        action =request.form['action'] 
        if action == 'Submit' :
            imagetext = request.form['imagetext'] 
            helpers.save_image_text(user.username, imagefilename, imagetext)
        elif action == 'Delete' :
            helpers.delete_one_image_file(user.username, imagefilename);
        
        return images()
        
    return redirect(url_for('login'))    


    
# ======== Main ================================= #
if __name__ == "__main__":
    app.run(debug=True, use_reloader=True, host="0.0.0.0")
