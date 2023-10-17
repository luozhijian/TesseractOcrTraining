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
from threading import Thread
werkzeug.serving._log_add_style = False

app = Flask(__name__)

app.secret_key = 'TesseractOcrTraining' # Generic key for dev purposes only
logger =None 

logger = logging.getLogger('MainProgram')
file_handler = logging.handlers.RotatingFileHandler('/var/log/tesseracttraining/tesseracttraining.log', maxBytes=2000000, backupCount=50)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)
helpers.logger = logger
training_in_process = False    
    
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
    try :
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
                            return json.dumps({'status': 'Login successful'})
                        return json.dumps({'status': 'Invalid user/pass'})
                    return json.dumps({'status': 'Both fields required'})
            except :
                pass #eat the error
            return render_template('login.html', form=form)

        user = helpers.get_user()
        if user :
            logger.info('%s login refresh'%user.username)
        # return images()
        return render_template('home.html', user=user)
    except Exception as e :
        if logger :
            logger.exception(e)

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
        logger.info("did not login forward to login")       
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
    logger.info("imagefiles did not login forward to login")       
    return redirect(url_for('login'))
        
@app.route('/download/<name>')
def download(name):
    # print('result: %s'%name)
    if session.get('logged_in'):
        username = helpers.get_username()
        result_folder = helpers.generate_image_folder(username)
        filename_with_path = request.args.get("path")
        filename_with_path_unquoted = urllib.parse.unquote_plus(filename_with_path)
        path_part, filenamePart = os.path.split(filename_with_path_unquoted)
        print (path_part)
        print (filenamePart)
        real_folder = os.path.join( result_folder, path_part)
        
        path_real_folder = Path(real_folder)
        path_result_folder = Path(result_folder)
        if (not path_part ) or path_part == "." or path_result_folder in path_real_folder.parents :
            # print ('%s    %s'%(real_folder, name) )
            return send_from_directory(real_folder, filenamePart)
        else :
            raise Exception("Unknow file name: %s/%s"%(name, filename_with_path_unquoted) )
    # print("resultfiles did not login forward to login")       
    logger.info("resultfiles did not login forward to login")       
    return redirect(url_for('login'))
        
        

# -------- results --------------- #
@app.route('/results', methods=['GET', 'POST'])
def results():
    if session.get('logged_in'):
        user = helpers.get_user()
        # list the content in result folder, and for download
        folder_type =  'results' 
        results = helpers.list_folder_result(user.username, folder_type )
        return render_template('files_for_download.html', results=results, folder_type =folder_type)
    logger.info("results did not login forward to login")       
    return redirect(url_for('login'))


# -------- logs --------------- #
@app.route('/logs', methods=['GET', 'POST'])
def logs():
    if session.get('logged_in'):
        user = helpers.get_user()
        # list the content in logs folder, and for download
        folder_type =  'logs' 
        results = helpers.list_folder_result(user.username, folder_type  )
        return render_template('files_for_download.html', results=results, folder_type =folder_type)
    logger.info("results did not login forward to login")       
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
        logger.info("upload did not login forward to login")       
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
            start_templates = helpers.get_all_template(user.username )
            message_is_running=''
            enable_disable =''
            if  training_in_process :
                message_is_running ="Another user is running the training, can only one user can use it at the same time, please visit late to check"
                enable_disable ='disabled'
            return render_template('training.html', templates=start_templates, message_is_running = message_is_running,  enable_disable= enable_disable)
        logger.info("training did not login forward to login")
        return redirect(url_for('login'))    
    except Exception as e :
        if logger :
            logger.exception(e)
        return handle_exception(e)

def threaded_function_start_training(args):
    global training_in_process
    try :
        print ('in threaded_function_start_training')
        (is_validate_command, command_list, logfilename ) =args
        with  open(logfilename, 'a', encoding="utf-8")  as the_logfile  :
            try :
                if training_in_process :
                    raise Exception( 'Another training already in process')
                training_in_process = True
                the_logfile.write( command_list)
                the_logfile.flush()
                if is_validate_command :
                    # command_list ="dir && ping -t localhost"
                    p = subprocess.Popen(command_list, stdout=the_logfile, stderr=subprocess.STDOUT, shell=True)
                    p.wait()
                the_logfile.flush()
                the_logfile.write('\n\nCompleted: %s'%logfilename)
            except Exception as e :
                print(e)
                the_logfile.write(e)
                the_logfile.flush()
                if logger :
                    logger.exception(e)            
    except Exception as e2 :
        if logger :
            logger.exception(e2)     
    finally :
        training_in_process =False

# -------- start_training --------------- #
@app.route('/start_training', methods=['POST'])
def start_training():
    print('start_training')
    try :
        if session.get('logged_in'):
            user = helpers.get_user()
            start_template=''
            try :
                start_template = request.form['templatename']
            except :
                pass
            model_name = request.form['model_name']
            more_parameters = request.form['more_parameters']
    #        helpers.start_training_process(user.username, start_template)
            session["start_template"]=start_template
            session["model_name"]=model_name
            session["more_parameters"]=more_parameters
            
            if model_name :
                username = helpers.get_username()
                model_name = model_name.strip()
                start_model_string =''
                if  len(start_template ) >0 :
                    start_model_string = " START_MODEL=" + start_template
                result_dir = helpers.generate_result_folder(username, "results")
                ground_truth_dir = helpers.generate_image_folder(username)
                result_dir_model = os.path.join(result_dir, model_name)
                if os.path.exists(result_dir_model) :
                    new_path = result_dir_model + '_'+ datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S%f')
                    shutil.move(result_dir_model, new_path) 
                if os.path.exists(result_dir_model +'.traineddata') :
                    new_path_2= result_dir_model+'.traineddata' + '_'+ datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S%f')
                    shutil.move(result_dir_model +'.traineddata', new_path_2) 
                copy_command_1 ='mv -v ./data/%s %s' %(model_name, result_dir ) 
                copy_command_2 ='mv -v ./data/%s.traineddata %s' %(model_name, result_dir ) 
                copy_command = copy_command_1 +  ' &&  ' +  copy_command_2
                command_list = 'cd /usr/local/src/tesstrain  && rm  -d -r data   && make tesseract-langdata ' \
                       + 'make training MODEL_NAME=%s %s GROUND_TRUTH_DIR=%s %s'%(model_name, start_model_string, ground_truth_dir, more_parameters) + ' && ' +copy_command
                is_validate_command = True
                (logfilename, log_filename_only)= helpers.get_current_log_name(username)
                session["logfilename"]=logfilename
                thread = Thread(target = threaded_function_start_training, args= ((is_validate_command, command_list, logfilename ),)  )
                thread.start()
        
            
            
            return render_template('training_in_process.html', start_template=model_name, logfilename =log_filename_only)
        logger.info("start_training did not login forward to login")       
        return redirect(url_for('login'))    
    except Exception as e :
        print(e)
        if logger :
            logger.exception(e)
        return handle_exception(e)

@app.route('/stream')
def stream():
    try :
        print('stream')
        # print (logfilename_only)
        if session.get('logged_in') : 
            
            logfilename =session["logfilename"]
            print ('cached filename: ' + logfilename);
            if not logfilename : #or not logfilename_only in logfilename:
                logger.error('not find log filename  ')
                return redirect(url_for('login'))   
             # print(command_list)
             
            def generate():
                for line in Pygtail(logfilename, every_n=1):
                    yield "data:" + str(line) + "\n\n"
                    time.sleep(0.1) 

                yield  "data:" + 'close' + "\n\n" + "\n\n"
                
            return Response(generate(), mimetype= 'text/event-stream')
        return redirect(url_for('login'))   
    except Exception as e :
        print(e)
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
        logger.info("imageedit did not login forward to login")       
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
            
        logger.info("savetext did not login forward to login ")       
        return redirect(url_for('login'))    
    except Exception as e :
        if logger :
            logger.exception(e)
        return handle_exception(e)

# ======== Main ================================= #
if __name__ == "__main__":

    app.run(debug=True, use_reloader=True, host="0.0.0.0")
    

