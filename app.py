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
import logging
import logging.handlers
import subprocess
import urllib.parse
from werkzeug.exceptions import HTTPException
from pathlib import Path
import shutil
import werkzeug
import datetime
werkzeug.serving._log_add_style = False

app = Flask(__name__)

app.secret_key = os.urandom(12)  # Generic key for dev purposes only
logger =None 

logger = logging.getLogger('MainProgram')
file_handler = logging.handlers.RotatingFileHandler('/var/log/tesseracttraining/tesseracttraining.log', maxBytes=2000000, backupCount=50)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)
helpers.logger = logger
    
    
#  some code is from Flaskex

@app.route("/<string:path>", methods=['GET', 'POST'])
@app.route("/<path:path>", methods=['GET', 'POST'])
def index2(path):
    return path
    
@app.route('/favicon.ico') 
def favicon(): 
    return send_from_directory(os.path.join(app.root_path, 'static/icons'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    
    
@app.errorhandler(404)
def page_not_found(e):
    # your processing here
    return ''

@app.errorhandler(Exception)
def handle_exception(e):
    path = request.path
    if logger :
        logger.exception(e)
        logger.error('error path:' + path)
    # pass through HTTP errors
    # if isinstance(e, HTTPException):
        # return e

    # now you're handling non-HTTP exceptions only
    return render_template("500_generic.html", e=e), 500
    
    
# ======== Routing =  #
# -------- Login ----- #
@app.route('/', methods=['GET', 'POST'])
def login():
    if not session.get('logged_in'):
        form = forms.LoginForm(request.form)
        try :
            if request.method == 'POST':
                username = request.form['username'].lower()
                password = request.form['password']
                if form.validate():
                    if helpers.credentials_valid(username, password):
                        session['logged_in'] = True
                        session['username'] = username
                        logger.info('%s login json'% username)
                        return json.dumps({'status': 'Login successful'})
                    return json.dumps({'status': 'Invalid user/pass'})
                return json.dumps({'status': 'Both fields required'})
        except :
            pass #eat the error
        return render_template('login.html', form=form)
    user = helpers.get_user()
    if user :
        logger.info('%s login refresh'%user.username)
    return images()
    # return render_template('home.html', user=user)


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
                    logger.info('%s %s signup'% (username,email) )
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
    try:
        if session.get('logged_in'):
            user = helpers.get_user()
            # list, get bitmap and linked text file
            filepairs = helpers.list_folder_image_text_pair(user.username )
            return render_template('images.html', user=user, filepairs = filepairs)
        return redirect(url_for('login'))
    except Exception as e :
        if logger :
            logger.exception(e)
    
@app.route('/imagefiles/<name>')
def imagefiles(name):
    # print('imagefile%s'%name)
    if session.get('logged_in'):
        username = helpers.get_username()
        return send_from_directory(helpers.generate_image_folder(username), name)
    return redirect(url_for('login'))
        
@app.route('/resultfiles/<name>')
def resultfiles(name):
    # print('result: %s'%name)
    if session.get('logged_in'):
        username = helpers.get_username()
        result_folder = helpers.generate_result_folder(username)
        file_path = request.args.get("path")
        name_file_path = urllib.parse.unquote_plus(file_path)
        real_folder = os.path.join( result_folder, name_file_path)
        
        path_real_folder = Path(real_folder)
        path_result_folder = Path(result_folder)
        if name_file_path == "." or path_result_folder in path_real_folder.parents :
            print ('%s    %s'%(real_folder, name) )
            return send_from_directory(real_folder, name)
        else :
            raise Exception("Unknow file name: %s/%s"%(name_file_path, name) )
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
    try :
        if session.get('logged_in'):
            user = helpers.get_user()
            
            files = request.files.getlist("fileupload")
            
            # fileitem = request.files['fileupload']
            for file in files:
                e = helpers.save_image_file(user.username, file)
                
            return images()

        return redirect(url_for('login'))
    except Exception as e :
        if logger :
            logger.exception(e) 
        return handle_exception(e)

# -------- training --------------- #
@app.route('/training', methods=['GET'])
def training():
    try:
        if session.get('logged_in'):
            user = helpers.get_user()
            start_templateS = helpers.get_all_template(user.username )
            return render_template('training.html', templateS=start_templateS)
        return redirect(url_for('login'))    
    except Exception as e :
        if logger :
            logger.exception(e)
        return handle_exception(e)

# -------- start_training --------------- #
@app.route('/start_training', methods=['POST'])
def start_training():
    try :
        if session.get('logged_in'):
            user = helpers.get_user()
            start_template = request.form['templatename']
            model_name = request.form['model_name']
            more_parameters = request.form['more_parameters']
    #        helpers.start_training_process(user.username, start_template)
            session["start_template"]=start_template
            session["model_name"]=model_name
            session["more_parameters"]=more_parameters
            return render_template('training_in_process.html', start_template=model_name)
        return redirect(url_for('login'))    
    except Exception as e :
        if logger :
            logger.exception(e)
        return handle_exception(e)

@app.route('/stream')
def stream():
    try :
        if session.get('logged_in'):
            command_list = ''
            p = None
            the_file=None
            try :
                username = helpers.get_username()
                start_template =session["start_template"]
                model_name = session["model_name"]
                more_parameters =session["more_parameters"]
                more_parameters = helpers.remove_special_char(more_parameters)
                if model_name :
                    model_name = model_name.strip()
                    result_dir = helpers.generate_result_folder(username)
                    ground_truth_dir = helpers.generate_image_folder(username)
                    result_dir_model = os.path.join(result_dir, model_name)
                    if os.path.exists(result_dir_model) :
                        new_path = result_dir_model + '_'+ datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S%f')
                        shutil.move(result_dir_model, new_path) 
                    copy_command ='mv -v ./data/%s %s' %(model_name, result_dir ) 
                    command_list = 'cd /usr/local/src/tesstrain && ' + 'make training MODEL_NAME=%s GROUND_TRUTH_DIR=%s %s'%(model_name, ground_truth_dir, more_parameters) + ' && ' +copy_command
                    is_validate_command = True
                    logfilename= helpers.get_current_log_name(username)
                    the_file = open(logfilename, 'a') 
                    if is_validate_command :
                        # command_list ="dir && ping -t localhost"
                        p = subprocess.Popen(command_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

                else :
                    command_list='empty model name'
            except Exception as ex:
                    command_list += '\n' + str(ex) 
                    p = None
            print(command_list)
            def generate():
                if the_file :
                    the_file.write(command_list + '\n')
                yield "data:" + command_list  + "\n\n" + "\n\n"
                if p :
                    while(True):
                        line = p.stdout.readline()
                        if line:
                            print(line)
                            line =str(line, "utf-8")
                            the_file.write(line + "\n")
                            yield "data:" + line + "\n\n" + "\n\n"
                        elif not p.poll():
                            break
                            

                if the_file :
                    the_file.close()
                yield  "data:" + 'close' + "\n\n" + "\n\n"
                
            return Response(generate(), mimetype= 'text/event-stream')
        return redirect(url_for('login'))   
    except Exception as e :
        if logger :
            logger.exception(e)  
        return handle_exception(e)
    

@app.route('/imageedit', methods=['GET'])
def imageedit():
    try:
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
    except Exception as e :
        if logger :
            logger.exception(e)
        return handle_exception(e)

@app.route('/savetext', methods=['GET', 'POST' ])
def savetext():
    try:
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
    except Exception as e :
        if logger :
            logger.exception(e)
        return handle_exception(e)

# ======== Main ================================= #
if __name__ == "__main__":

    app.run(debug=True, use_reloader=True, host="0.0.0.0")
    

