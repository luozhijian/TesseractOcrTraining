# -*- coding: utf-8 -*-

from scripts import tabledef
from scripts import forms
from scripts import helpers
from scripts import version
from flask import Flask, redirect, url_for, render_template, request, session, send_from_directory, Response, send_file, after_this_request
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
import zipfile
import tempfile
import werkzeug
import datetime
from threading import Thread
try:
    import psutil
except ImportError:
    psutil = None
werkzeug.serving._log_add_style = False

app = Flask(__name__)

app.secret_key = 'TesseractOcrTraining' # Generic key for dev purposes only

log_file_path = '/var/log/tesseracttraining/tesseracttraining.log'
# Make version information available to all templates
@app.context_processor
def inject_version():
    return dict(app_version=version.get_version(), 
                app_version_info=version.get_full_version_info())

logger =None 

logger = logging.getLogger('MainProgram')
file_handler = logging.handlers.RotatingFileHandler(log_file_path, maxBytes=2000000, backupCount=50)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)
helpers.logger = logger
training_in_process = False    
training_in_process_datetime =''


def _get_system_info():
    system_drive = Path(app.root_path).anchor or '/'
    cpu_percent = None
    memory_percent = None

    if psutil:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.2)
        except Exception:
            cpu_percent = None
        try:
            memory_percent = psutil.virtual_memory().percent
        except Exception:
            memory_percent = None

    disk_usage = shutil.disk_usage(system_drive)
    free_disk_gb = round(disk_usage.free / (1024 ** 3), 2)

    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory_percent,
        'free_disk_gb': free_disk_gb,
        'system_drive': system_drive,
    }


def _get_training_status_info():
    global training_in_process_datetime
    global training_in_process
    started_at = training_in_process_datetime if training_in_process else None
    minutes_ago = None
    can_stop = False

    if started_at:
        elapsed_seconds = max((datetime.datetime.now() - started_at).total_seconds(), 0)
        minutes_ago = int(elapsed_seconds // 60)
        can_stop = elapsed_seconds >= 30 * 60

    return {
        'training_in_process': training_in_process,
        'training_in_process_datetime': started_at,
        'minutes_ago': minutes_ago,
        'can_stop': can_stop,
    }


def _read_last_log_bytes(file_path, byte_count=10000):
    try:
        with open(file_path, 'rb') as log_file:
            log_file.seek(0, os.SEEK_END)
            file_size = log_file.tell()
            seek_position = max(file_size - byte_count, 0)
            log_file.seek(seek_position)
            log_bytes = log_file.read(byte_count)
            return log_bytes.decode('utf-8', errors='replace')
    except Exception as e:
        if logger:
            logger.exception(e)
        return 'Unable to read log content.'
    
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
    return render_template('404.html'), 404

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
                password = request.form['password']
                username = request.form['username'].lower()
                # if form.validate():
                if username:
                    if helpers.credentials_valid(username, password):
                        session['logged_in'] = True
                        session['username'] = username
                        return json.dumps({'status': 'Login successful'})
                        #return images()
                    return json.dumps({'status': 'Invalid user/pass'})
                return render_template('login.html', form=form)
            except :
                return render_template('login.html', form=form)

        user = helpers.get_user()
        if user :
            logger.info('%s login refresh'%user.username)
        #return images()
        return render_template('home.html', user=user)
    except Exception as e :
        if logger :
            logger.exception(e)
        return json.dumps({'status': str(e)})

@app.route("/logout")
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'))


@app.route('/system_info', methods=['GET'])
def system_info():
    if session.get('logged_in'):
        user = helpers.get_user()
        show_log_tail = user and user.username == 'luozhijian'
        log_tail_content = _read_last_log_bytes(log_file_path, 10000) if show_log_tail else ''
        return render_template(
            'system_info.html',
            user=user,
            system_info=_get_system_info(),
            training_status=_get_training_status_info(),
            server_datetime=datetime.datetime.now(),
            show_log_tail=show_log_tail,
            log_tail_content=log_tail_content,
            log_file_path=log_file_path,
            status_message=request.args.get('message', ''),
            status_type=request.args.get('status_type', 'is-info')
        )
    return redirect(url_for('login'))


@app.route('/stop_training', methods=['POST'])
def stop_training():
    global training_in_process

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if not training_in_process:
        return redirect(url_for('system_info', message='No training is currently in process.', status_type='is-warning'))

    training_status = _get_training_status_info()
    if not training_status['can_stop']:
        return redirect(
            url_for(
                'system_info',
                message='You have to wait at least 30 minutes to stop it, please wait and then refresh the page to Stop it.',
                status_type='is-warning'
            )
        )

    if request.form.get('stop_confirmation', '').strip().lower() != 'stop':
        return redirect(url_for('system_info', message='Stop request cancelled. Type stop to continue.', status_type='is-warning'))

    training_in_process = False
    return redirect(url_for('system_info', message='training_in_process has been set to False.', status_type='is-success'))


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
                # Validate username for path safety
                if not helpers.username_isvalid(username):
                    return json.dumps({'status': 'Invalid username. Use only letters, numbers, hyphens, and underscores. Must start with letter/number. not windows or linux reserva'})
                
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

# -------- Robots & Sitemap (SEO) --------------- #
@app.route('/robots.txt')
def robots_txt():
    lines = [
        "User-agent: *",
        "Allow: /",
        "Sitemap: " + request.url_root.rstrip('/') + "/sitemap.xml",
    ]
    return Response("\n".join(lines), mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap_xml():
    try:
        pages = []
        base_url = request.url_root.rstrip('/')
        # Public pages
        pages.extend([
            (base_url + '/', 'weekly'),
            (base_url + '/forum', 'daily'),
        ])
        # Forum posts
        with helpers.session_scope() as db_session:
            posts = db_session.query(tabledef.ForumPost).order_by(tabledef.ForumPost.created_at.desc()).limit(100).all()
            for post in posts:
                pages.append((f"{base_url}/forum/post/{post.id}", 'weekly'))
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        ]
        for loc, freq in pages:
            xml_parts.append('<url>')
            xml_parts.append(f'<loc>{loc}</loc>')
            xml_parts.append(f'<changefreq>{freq}</changefreq>')
            xml_parts.append('</url>')
        xml_parts.append('</urlset>')
        return Response("".join(xml_parts), mimetype='application/xml')
    except Exception as e:
        if logger:
            logger.exception(e)
        return Response('', mimetype='application/xml')

@app.route('/users', methods=['GET'])
def users():
    """View all users with created and last access dates - accessible to everyone."""
    try:
        with helpers.session_scope() as db_session:
            db_users = db_session.query(tabledef.User).order_by(tabledef.User.username.asc()).all()
            users_with_dates = []
            for db_user in db_users:
                users_with_dates.append({
                    'username': db_user.username,
                    'email': db_user.email,
                    'created_date': db_user.created_date,
                    'last_access_date': db_user.last_access_date,
                })

            return render_template('users.html', users=sorted(users_with_dates, key=lambda x: x['last_access_date'], reverse=True)  )
    except Exception as e:
        if logger:
            logger.exception(e)
        return handle_exception(e)


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

@app.route('/images/download_all_zip', methods=['GET'])
def download_all_zip():
    """Download all files in user's root image folder (no subfolders) as a zip."""
    try:
        if session.get('logged_in'):
            username = helpers.get_username()
            user_folder = helpers.generate_image_folder(username)
            logger.info("download_all_zip: " + user_folder)
            zip_basename = f"{username}_images.zip"
            fd, zip_path = tempfile.mkstemp(suffix=".zip", prefix=f"{username}_", dir=user_folder)
            os.close(fd)
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for entry_name in os.listdir(user_folder):
                        if entry_name.endswith('.zip'):
                            continue
                        entry_full_path = os.path.join(user_folder, entry_name)
                        if os.path.isfile(entry_full_path):
                            zip_file.write(entry_full_path, arcname=entry_name)

                @after_this_request
                def remove_created_zip(response):
                    try:
                        if os.path.exists(zip_path):
                            os.remove(zip_path)
                    except Exception as cleanup_error:
                        if logger:
                            logger.warning(f"Failed to remove temporary zip file {zip_path}: {cleanup_error}")
                    return response

                return send_file(
                    zip_path,
                    as_attachment=True,
                    download_name=zip_basename,
                    mimetype='application/zip'
                )
            except Exception:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                raise
        logger.info("download_all_zip did not login forward to login")
        return redirect(url_for('login'))
    except Exception as e:
        if logger:
            logger.exception(e)
        return handle_exception(e)

@app.route('/images/delete_all', methods=['POST'])
def delete_all_images():
    """Delete all files and folders under user's image folder, recursively."""
    try:
        if session.get('logged_in'):
            username = helpers.get_username()
            user_folder = helpers.generate_image_folder(username)
            if os.path.isdir(user_folder):
                for dirpath, dirnames, filenames in os.walk(user_folder, topdown=False):
                    for filename in filenames:
                        full_filename = os.path.join(dirpath, filename)
                        os.remove(full_filename)
                    for dirname in dirnames:
                        full_dirname = os.path.join(dirpath, dirname)
                        os.rmdir(full_dirname)
            return redirect(url_for('images'))
        logger.info("delete_all_images did not login forward to login")
        return redirect(url_for('login'))
    except Exception as e:
        if logger:
            logger.exception(e)
        return handle_exception(e)

          
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

@app.route('/view/<name>')
def view_file(name):
    """View text file content in browser"""
    if session.get('logged_in'):
        username = helpers.get_username()
        result_folder = helpers.generate_image_folder(username)
        filename_with_path = request.args.get("path")
        filename_with_path_unquoted = urllib.parse.unquote_plus(filename_with_path)
        path_part, filenamePart = os.path.split(filename_with_path_unquoted)
        real_folder = os.path.join(result_folder, path_part)
        
        path_real_folder = Path(real_folder)
        path_result_folder = Path(result_folder)
        if (not path_part) or path_part == "." or path_result_folder in path_real_folder.parents:
            file_path = os.path.join(real_folder, filenamePart)
            
            # Check if file exists and is a text file
            if os.path.exists(file_path):
                _, ext = os.path.splitext(filenamePart.lower())
                if ext in ['.txt', '.log', '.md', '.py', '.html', '.css', '.js', '.json', '.xml', '.csv']:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        return render_template('file_viewer.html', 
                                             filename=filenamePart, 
                                             content=content,
                                             file_type=ext[1:] if ext else 'text')
                    except UnicodeDecodeError:
                        # If UTF-8 fails, try with different encoding
                        try:
                            with open(file_path, 'r', encoding='latin-1') as f:
                                content = f.read()
                            return render_template('file_viewer.html', 
                                                 filename=filenamePart, 
                                                 content=content,
                                                 file_type=ext[1:] if ext else 'text')
                        except Exception as e:
                            return f"Error reading file: {str(e)}", 500
                else:
                    # For non-text files, redirect to download
                    return redirect(url_for('download', name=name, path=filename_with_path))
            else:
                return "File not found", 404
        else:
            raise Exception("Unknown file name: %s/%s" % (name, filename_with_path_unquoted))
    
    logger.info("view_file did not login forward to login")
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
        return render_template('files_for_display.html', results=results, folder_type =folder_type)
    logger.info("results did not login forward to login")       
    return redirect(url_for('login'))
    
   
# -------- serve forum images --------------- #
@app.route('/forum/image/<username>/<filename>')
def forum_image(username, filename):
    """Serve forum images - accessible to everyone"""
    try:
        forum_image_folder = helpers.generate_forum_image_folder(username)
        return send_from_directory(forum_image_folder, filename)
    except Exception as e:
        if logger:
            logger.exception(e)
        return handle_exception(e)

@app.route('/forum/image/<int:post_id>')
def forum_image_by_post(post_id):
    """Alternative route to serve forum images by post ID - accessible to everyone"""
    try:
        with helpers.session_scope() as db_session:
            post = db_session.query(tabledef.ForumPost).filter_by(id=post_id).first()
            if not post or not post.image_filename:
                return render_template('404.html'), 404
            
            forum_image_folder = helpers.generate_forum_image_folder(post.author.username)
            return send_from_directory(forum_image_folder, post.image_filename)
    except Exception as e:
        if logger:
            logger.exception(e)
        return handle_exception(e)

# ======== Forum ================================= #
@app.route('/forum', methods=['GET'])
def forum():
    """View all forum posts - accessible to everyone"""
    try:
        with helpers.session_scope() as db_session:
            posts = db_session.query(tabledef.ForumPost).order_by(
                tabledef.ForumPost.importance.desc(),
                tabledef.ForumPost.created_at.desc()
            ).all()
            return render_template('forum.html', posts=posts)
    except Exception as e:
        if logger:
            logger.exception(e)
        return handle_exception(e)

@app.route('/forum/post/<int:post_id>', methods=['GET'])
def forum_post(post_id):
    """View a specific forum post with replies - accessible to everyone"""
    try:
        with helpers.session_scope() as db_session:
            post = db_session.query(tabledef.ForumPost).filter_by(id=post_id).first()
            if not post:
                return render_template('404.html'), 404
            replies = db_session.query(tabledef.ForumReply).filter_by(post_id=post_id).order_by(tabledef.ForumReply.created_at.asc()).all()
            return render_template('forum_post.html', post=post, replies=replies)
    except Exception as e:
        if logger:
            logger.exception(e)
        return handle_exception(e)

@app.route('/forum/new', methods=['GET', 'POST'])
def forum_new_post():
    """Create a new forum post - requires login"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        if request.method == 'POST':
            title = request.form['title']
            content = request.form['content']
            
            if title and content:
                user = helpers.get_user()
                image_filename = None
                
                # Handle image upload if provided
                if 'image' in request.files:
                    image_file = request.files['image']
                    if image_file and image_file.filename:
                        try:
                            # Use new forum-specific save function
                            saved_message = helpers.save_forum_image_file(user.username, image_file)
                            # Extract just the filename from the message
                            image_filename = saved_message.replace(' saved', '')
                        except Exception as img_error:
                            if logger:
                                logger.warning(f"Failed to save forum image: {img_error}")
                            # Continue creating post even if image upload fails
                
                with helpers.session_scope() as db_session:
                    new_post = tabledef.ForumPost(
                        title=title,
                        content=content,
                        author_id=user.id,
                        created_at=datetime.datetime.now(),
                        image_filename=image_filename,
                        importance=0
                    )
                    db_session.add(new_post)
                    db_session.commit()
                    return redirect(url_for('forum_post', post_id=new_post.id))
            
        return render_template('forum_new_post.html')
    except Exception as e:
        if logger:
            logger.exception(e)
        return handle_exception(e)

@app.route('/forum/post/<int:post_id>/reply', methods=['POST'])
def forum_reply(post_id):
    """Add a reply to a forum post - requires login"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        content = request.form['content']
        
        if content:
            user = helpers.get_user()
            image_filename = None
            
            # Handle image upload if provided
            if 'image' in request.files:
                image_file = request.files['image']
                if image_file and image_file.filename:
                    try:
                        # Use forum-specific save function
                        saved_message = helpers.save_forum_image_file(user.username, image_file)
                        # Extract just the filename from the message
                        image_filename = saved_message.replace(' saved', '')
                    except Exception as img_error:
                        if logger:
                            logger.warning(f"Failed to save forum reply image: {img_error}")
                        # Continue creating reply even if image upload fails
            
            with helpers.session_scope() as db_session:
                # Check if post exists
                post = db_session.query(tabledef.ForumPost).filter_by(id=post_id).first()
                if not post:
                    return render_template('404.html'), 404
                
                new_reply = tabledef.ForumReply(
                    content=content,
                    author_id=user.id,
                    post_id=post_id,
                    created_at=datetime.datetime.now(),
                    image_filename=image_filename
                )
                db_session.add(new_reply)
                db_session.commit()
        
        return redirect(url_for('forum_post', post_id=post_id))
    except Exception as e:
        if logger:
            logger.exception(e)
        return handle_exception(e)

@app.route('/forum/post/<int:post_id>/importance', methods=['POST'])
def update_post_importance(post_id):
    """Update post importance - only for users starting with 'luozhijian'"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        # Check if user is authorized (username starts with 'luozhijian')
        username = session.get('username', '')
        if not username.startswith('luozhijian'):
            return redirect(url_for('forum'))
        
        importance = request.form.get('importance', 0)
        try:
            importance = int(importance)
        except ValueError:
            importance = 0
        
        with helpers.session_scope() as db_session:
            post = db_session.query(tabledef.ForumPost).filter_by(id=post_id).first()
            if post:
                post.importance = importance
                db_session.commit()
        
        return redirect(url_for('forum'))
    except Exception as e:
        if logger:
            logger.exception(e)
        return handle_exception(e)

@app.route('/forum/post/<int:post_id>/edit', methods=['GET', 'POST'])
def forum_edit_post(post_id):
    """Edit a forum post - only by original author"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        with helpers.session_scope() as db_session:
            post = db_session.query(tabledef.ForumPost).filter_by(id=post_id).first()
            if not post:
                return render_template('404.html'), 404
            
            user = helpers.get_user()
            if post.author_id != user.id:
                return render_template('403.html'), 403
            
            if request.method == 'POST':
                title = request.form['title']
                content = request.form['content']
                
                if title and content:
                    post.title = title
                    post.content = content
                    post.updated_at = datetime.datetime.now()
                    
                    # Handle image changes
                    remove_image = request.form.get('remove_image')
                    new_image = request.files.get('image')
                    
                    # If user wants to remove current image
                    if remove_image == '1':
                        if post.image_filename:
                            # Delete old image file
                            try:
                                old_image_path = os.path.join(
                                    helpers.generate_forum_image_folder(post.author.username),
                                    post.image_filename
                                )
                                if os.path.exists(old_image_path):
                                    os.remove(old_image_path)
                            except Exception as e:
                                if logger:
                                    logger.warning(f"Failed to delete old forum image: {e}")
                        post.image_filename = None
                    
                    # If user uploaded a new image
                    elif new_image and new_image.filename:
                        try:
                            # Delete old image file if it exists
                            if post.image_filename:
                                old_image_path = os.path.join(
                                    helpers.generate_forum_image_folder(post.author.username),
                                    post.image_filename
                                )
                                if os.path.exists(old_image_path):
                                    os.remove(old_image_path)
                            
                            # Save new image
                            saved_message = helpers.save_forum_image_file(post.author.username, new_image)
                            post.image_filename = saved_message.replace(' saved', '')
                        except Exception as img_error:
                            if logger:
                                logger.warning(f"Failed to save new forum image: {img_error}")
                    
                    db_session.commit()
                    return redirect(url_for('forum_post', post_id=post.id))
            
            return render_template('forum_edit_post.html', post=post)
    except Exception as e:
        if logger:
            logger.exception(e)
        return handle_exception(e)

@app.route('/forum/reply/<int:reply_id>/edit', methods=['GET', 'POST'])
def forum_edit_reply(reply_id):
    """Edit a forum reply - only by original author"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        with helpers.session_scope() as db_session:
            reply = db_session.query(tabledef.ForumReply).filter_by(id=reply_id).first()
            if not reply:
                return render_template('404.html'), 404
            
            user = helpers.get_user()
            if reply.author_id != user.id:
                return render_template('403.html'), 403
            
            if request.method == 'POST':
                content = request.form['content']
                
                if content:
                    reply.content = content
                    reply.updated_at = datetime.datetime.now()
                    
                    # Handle image changes
                    remove_image = request.form.get('remove_image')
                    new_image = request.files.get('image')
                    
                    # If user wants to remove current image
                    if remove_image == '1':
                        if reply.image_filename:
                            # Delete old image file
                            try:
                                old_image_path = os.path.join(
                                    helpers.generate_forum_image_folder(reply.author.username),
                                    reply.image_filename
                                )
                                if os.path.exists(old_image_path):
                                    os.remove(old_image_path)
                            except Exception as e:
                                if logger:
                                    logger.warning(f"Failed to delete old forum reply image: {e}")
                        reply.image_filename = None
                    
                    # If user uploaded a new image
                    elif new_image and new_image.filename:
                        try:
                            # Delete old image file if it exists
                            if reply.image_filename:
                                old_image_path = os.path.join(
                                    helpers.generate_forum_image_folder(reply.author.username),
                                    reply.image_filename
                                )
                                if os.path.exists(old_image_path):
                                    os.remove(old_image_path)
                            
                            # Save new image
                            saved_message = helpers.save_forum_image_file(reply.author.username, new_image)
                            reply.image_filename = saved_message.replace(' saved', '')
                        except Exception as img_error:
                            if logger:
                                logger.warning(f"Failed to save new forum reply image: {img_error}")
                    
                    db_session.commit()
                    return redirect(url_for('forum_post', post_id=reply.post_id))
            
            return render_template('forum_edit_reply.html', reply=reply)
    except Exception as e:
        if logger:
            logger.exception(e)
        return handle_exception(e)

# -------- version information --------------- #
@app.route('/version')
def app_version():
    """Return version information as JSON"""
    return version.get_full_version_info()

@app.route('/api/version')
def api_version():
    """API endpoint for version information"""
    return {
        "application": "Tesseract OCR Training",
        "version": version.get_version(),
        "build_date": version.BUILD_DATE,
        "release_name": version.RELEASE_NAME
    }

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
            filepairs = helpers.list_folder_image_text_pair(user.username)
            message_is_running=''
            enable_disable =''
            if  training_in_process :
                message_is_running ="Another user is running the training, can only one user can use it at the same time, please visit SystemInfo page to check if you can stop it"
                enable_disable ='disabled'
            return render_template(
                'training.html',
                templates=start_templates,
                filepairs=filepairs,
                message_is_running=message_is_running,
                enable_disable=enable_disable
            )
        logger.info("training did not login forward to login")
        return redirect(url_for('login'))    
    except Exception as e :
        if logger :
            logger.exception(e)
        return handle_exception(e)

def threaded_function_start_training(args):
    global training_in_process
    global training_in_process_datetime
    try :

        (is_validate_command, command_list, logfilename ) =args
        logger.info ('In threaded_function_start_training: %s' % command_list)
        with  open(logfilename, 'a', encoding="utf-8")  as the_logfile  :
            try :
                if training_in_process :
                    raise Exception( 'Another training already in process')
                training_in_process = True
                training_in_process_datetime = datetime.datetime.now()
                the_logfile.write( command_list)
                the_logfile.write('\n\t\n\t\nThere is possible the log failed to refresh in middle, please do not refresh,\n but go Menu Logs to see the logs\n\t\n\t\n')
 
                the_logfile.flush()
                if is_validate_command :
                    # command_list ="dir && ping -t localhost"
                    p = subprocess.Popen(command_list, stdout=the_logfile, stderr=subprocess.STDOUT, shell=True)
                    p.wait()
                the_logfile.flush()
                the_logfile.write('\n\nCompleted: %s'%logfilename)
                training_in_process =False
            except Exception as e :
                training_in_process = False
                the_logfile.write(str(e))
                the_logfile.flush()
                if logger :
                    logger.exception(e)            
    except Exception as e2 :
        if logger :
            logger.exception(e2)     
    finally :
        training_in_process =False
        pass

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
                command_list = 'cd /usr/local/src/tesstrain  && rm  -d -r -f data   && mkdir data && ' \
                       + 'make training TESSDATA=/usr/local/src/tesstrain/tessdata_best DATA_DIR=/usr/local/src/tesstrain/data MODEL_NAME=%s %s GROUND_TRUTH_DIR=%s %s'%(model_name, start_model_string, ground_truth_dir, more_parameters) + ' && ' +copy_command
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

    app.run(debug=True, port=5000, use_reloader=True, host="0.0.0.0")
    

