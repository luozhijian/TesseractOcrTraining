# -*- coding: utf-8 -*-

from scripts import tabledef
from flask import session
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from requests.structures import CaseInsensitiveDict
import bcrypt
import os
from PIL import Image, UnidentifiedImageError
from datetime import datetime
import time
from threading import Thread
import urllib.parse


root_path ='/var/www/tesseracttraining/files'
root_path_tessdata ='/usr/local/src/tesstrain/usr/share/tessdata'
# root_path_tessdata = 'c:/temp'

current_log_name =None

logger =None

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    s = get_session()
    s.expire_on_commit = False
    try:
        yield s
        s.commit()
    except:
        s.rollback()
        raise
    finally:
        s.close()

def get_session():
    return sessionmaker(bind=tabledef.engine)()
    

def get_user():
    username = session['username']
    if username == 'demo':
        return tabledef.User(username='demo', password='1', email='demo@demo.com', id=0)  
    with session_scope() as s:
        user = s.query(tabledef.User).filter(tabledef.User.username.in_([username])).first()
        return user
        
        
def get_username():
    username = session['username']
    return username


def add_user(username, password, email):
    with session_scope() as s:
        u = tabledef.User(username=username, password=password.decode('utf8'), email=email)
        s.add(u)
        s.commit()


def change_user(**kwargs):
    username = session['username']
    with session_scope() as s:
        user = s.query(tabledef.User).filter(tabledef.User.username.in_([username])).first()
        for arg, val in kwargs.items():
            if val != "":
                setattr(user, arg, val)
        s.commit()


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())


def credentials_valid(username, password):
    try:    
        if username == 'demo' :
            return password == '1'
        with session_scope() as s:
            user = s.query(tabledef.User).filter(tabledef.User.username.in_([username])).first()
            if user:
                return bcrypt.checkpw(password.encode('utf8'), user.password.encode('utf8'))
            else:
                return False
    except Exception :
        return False

def username_isvalid(username):
    """
    Validate username to ensure it's safe as a directory name on both Linux and Windows.
    
    This function prevents:
    1. Windows device names (CON, PRN, COM1, etc.) - would cause file system errors
    2. Linux system names (root, sys, etc.) - could conflict with system accounts/directories
    3. Path traversal attacks (.. patterns)
    4. Invalid file system characters (< > : " | ? * \ /)
    5. Control characters and null bytes
    6. Names that start/end with dots or contain spaces
    7. Names that don't start with alphanumeric characters
    
    Returns True if valid, False otherwise.
    """
    import re
    import string
    
    if not username or not isinstance(username, str):
        return False
    
    # Check length (1-30 characters)
    if len(username) < 1 or len(username) > 30:
        return False
    
    # Application-specific reserved usernames
    app_reserved = ['demo', 'admin', 'administrator', 'test', 'guest', 'public']
    if username.lower() in app_reserved:
        return False
    
    # Windows reserved device names (case-insensitive)
    # These names are reserved by Windows regardless of extension
    windows_reserved = {
        # Console and printer devices
        'con', 'prn', 'aux', 'nul',
        # Serial communication ports
        'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9',
        # Parallel ports (line printer)
        'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
    }
    
    # Linux reserved/problematic names
    # These include system directories, device files, and common system users
    linux_reserved = {
        # System root user and common system accounts
        'root', 'daemon', 'bin', 'sys', 'sync', 'games', 'man', 'lp', 'mail', 
        'news', 'uucp', 'proxy', 'backup', 'list', 'irc', 'gnats', 'nobody',
        'systemd', 'syslog', 'messagebus', 'uuidd', 'dnsmasq', 'sshd',
        # Common service accounts
        'www', 'apache', 'nginx', 'mysql', 'postgres', 'redis', 'mongodb',
        'ftp', 'sftp', 'git', 'svn', 'jenkins', 'docker', 'kubernetes',
        # Device files from /dev/
        'null', 'zero', 'random', 'urandom', 'stdin', 'stdout', 'stderr', 
        'tty', 'console', 'kmsg', 'mem', 'disk', 'loop', 'block',
        # Important system directories
        'home', 'tmp', 'var', 'etc', 'usr', 'bin', 'sbin', 'dev', 'proc', 
        'sys', 'boot', 'lib', 'lib64', 'opt', 'mnt', 'media', 'run', 'srv',
        # Common mount points and directories
        'cdrom', 'floppy', 'usb', 'network', 'shared', 'public', 'temp',
        'cache', 'log', 'logs', 'backup', 'archive', 'download', 'uploads'
    }
    
    # Combine all reserved names
    all_reserved = windows_reserved | linux_reserved
    if username.lower() in all_reserved:
        return False
    
    # Check for Windows reserved names with extensions (e.g., "con.txt")
    base_name = username.lower().split('.')[0]
    if base_name in windows_reserved:
        return False
    
    # Invalid characters for both Windows and Linux paths
    # Windows: < > : " | ? * \ / and ASCII 0-31
    # Linux: only / and null character (but we'll be more restrictive)
    invalid_chars = set('<>:"|?*\\/\x00')
    invalid_chars.update(chr(i) for i in range(32))  # Control characters
    
    if any(char in invalid_chars for char in username):
        return False
    
    # Path traversal prevention
    if '..' in username or username.startswith('.') or username.endswith('.'):
        return False
    
    # No leading or trailing whitespace
    if username != username.strip():
        return False
    
    # No spaces at all (safer for command line operations)
    if ' ' in username:
        return False
    
    # Must contain only alphanumeric characters, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False
    
    # Must start with a letter or number (not underscore or hyphen)
    if not username[0].isalnum():
        return False
    
    # All checks passed
    return True
 

def username_taken(username):
    if username == 'demo':
        return False
    with session_scope() as s:
        return s.query(tabledef.User).filter(tabledef.User.username.in_([username])).first()

def generate_image_folder(username ) :
    return os.path.join(root_path, username) 

def generate_image_fullpath(username, image_filename ) :
    return os.path.join(root_path, username, image_filename) 

def generate_result_folder(username, folder_name) :
    if folder_name == 'images' :
        return generate_image_folder(username)
    return os.path.join(root_path, username, folder_name) 

def get_current_log_name(username ) :
    log_folder = os.path.join(root_path, username,'logs')
    create_folder_if_not_exists (log_folder)
    log_filename = 'log_' + datetime.utcnow().strftime('%Y%m%d_%H%M%S%f')+'.log'
    return (os.path.join(log_folder, log_filename), log_filename )

def remove_special_char(s ):
    if not s :
        return s
    return ''.join( c for c in s if  ( c.isalnum()  or c in ' /=\t' ) )
    
def get_txtfilename_from_image (username, image_filename) :
    image_filename_without_extension = image_filename[:-4]
    final_path = os.path.join(root_path, username, image_filename_without_extension + '.gt.txt')
    return final_path
    
def get_txtfilename_only_from_image (image_filename) :
    image_filename_gt = image_filename[:-4] + '.gt.txt'
    return image_filename_gt
      
def create_folder_if_not_exists(path_name) :
    #If folder doesn't exist, then create it
    if not os.path.isdir(path_name):
        os.makedirs(path_name)
        #print("created folder : ", path_name)


def list_folder_image_text_pair(username) :
    global root_path 
    final_path = generate_image_folder(username)
    create_folder_if_not_exists(final_path)
    list_of_files_1 = os.listdir(final_path)    
    if list_of_files_1 is None :
        list_of_files_1=[]
    list_of_files =[]
    
    for fname in list_of_files_1 :
        path = os.path.join(final_path, fname)
        if not os.path.isdir(path):
            list_of_files.append(fname)
        
    list_of_files.sort()
    
    hash_set = {v.lower():v for v in list_of_files }
    result =[]
    for one_file in list_of_files :
        if not one_file :
            continue 
        one_file_lower = one_file.lower()
        if one_file_lower.endswith('tif') or one_file_lower.endswith('png') :
            text_filename = get_txtfilename_only_from_image(one_file).lower()
            if text_filename in hash_set :
                text_filename_case_sensititive = hash_set[text_filename] 
                full_text_filename = os.path.join(final_path, text_filename_case_sensititive)
                text_content = open(full_text_filename, 'r').read()
                result.append( (one_file, text_filename_case_sensititive, text_content) )
            else :
                result.append( (one_file, '', '') )
        elif  not ( one_file_lower.endswith('.gt.txt')  or one_file_lower.endswith('.lstmf')  or one_file_lower.endswith('.box') ) :
            result.append( (one_file, '', '') )
            
    return result
   
def list_folder_result(username, folder) :
    global root_path 
    final_path = generate_result_folder(username, folder)
    user_path = generate_image_folder(username)
    create_folder_if_not_exists(final_path)
    list_of_files=[]
    for dir_, _, files in os.walk(final_path):
        for file_name in files:
            rel_dir = os.path.relpath(dir_, user_path)
            if not rel_dir  or rel_dir == '.' :   
                rel_file = file_name
            else :
                rel_file = os.path.join(rel_dir, file_name)
                
            list_of_files.append([urllib.parse.quote_plus(rel_file, safe='') , rel_file, file_name])
    list_of_files.sort()
    return list_of_files
    

def save_image_file(username, fileitem) :
    # check if the file has been uploaded
    try :
        final_filename=''
        if fileitem.filename:
            # strip the leading path from the file name
            fn = os.path.basename(fileitem.filename)
            fn_lower = fn.lower()
            final_filename = fn
            need_convert_image_file = False 
            #only png, tif is auto supported
            if  fn_lower.endswith('.bmp') or fn_lower.endswith('.jpg') or fn_lower.endswith('.jpeg') or fn_lower.endswith('.ico')  or fn_lower.endswith('.tiff') :
                final_filename =fn + '.png'
                need_convert_image_file = True
            final_filename_fullpath = os.path.join(root_path, username, final_filename)
           # open read and write the file into the server
            if need_convert_image_file :
                im = Image.open(fileitem)
                im.save(final_filename_fullpath)
            else :
                open(final_filename_fullpath, 'wb').write(fileitem.read())
        temp_messgage =  final_filename + ' saved'
        logger.info(temp_messgage)
        return temp_messgage
    except   Exception as e :
        raise e

def save_forum_image_file(username, fileitem):
    """Save forum image file to username/forum/ folder"""
    # check if the file has been uploaded
    try :
        final_filename=''
        if fileitem.filename:
            # strip the leading path from the file name
            fn = os.path.basename(fileitem.filename)
            fn_lower = fn.lower()
            final_filename = fn
            need_convert_image_file = False 
            #only png, tif is auto supported
            if  fn_lower.endswith('.bmp') or fn_lower.endswith('.jpg') or fn_lower.endswith('.jpeg') or fn_lower.endswith('.ico')  or fn_lower.endswith('.tiff') :
                final_filename =fn + '.png'
                need_convert_image_file = True
            
            # Create forum subfolder
            forum_folder = os.path.join(root_path, username, 'forum')
            create_folder_if_not_exists(forum_folder)
            
            final_filename_fullpath = os.path.join(forum_folder, final_filename)
           # open read and write the file into the server
            if need_convert_image_file :
                im = Image.open(fileitem)
                im.save(final_filename_fullpath)
            else :
                open(final_filename_fullpath, 'wb').write(fileitem.read())
        temp_messgage =  final_filename + ' saved'
        logger.info(temp_messgage)
        return temp_messgage
    except   Exception as e :
        raise e

def generate_forum_image_folder(username):
    """Generate the forum image folder path for a user"""
    return os.path.join(root_path, username, 'forum')

# return all current tesseract train data to begin with            
def get_all_template(username ) :
    template_path =root_path_tessdata
    list_of_files=None
    if os.path.isdir( template_path ):
        list_of_files_temp = os.listdir(template_path)
        list_of_files= [ s[:-12] for s in list_of_files_temp if s.lower().endswith('.traineddata') ]
    if list_of_files is None :
        list_of_files=[]
    else :
        list_of_files.append('')
    list_of_files.sort()
    return list_of_files
    
   
def save_image_text(username, image_filename, image_text) :
    final_path = get_txtfilename_from_image(username, image_filename)
    if not image_text : 
        if os.path.exists(final_path):
            os.remove(final_path)
    else :
        open(final_path, 'w').write(image_text)
 
def read_image_text(username, image_filename ) : 
    final_path = get_txtfilename_from_image(username, image_filename)

    if os.path.exists(final_path):
        text= open(final_path, 'r').read()
        return text
    return ''    #return empty instead of None

def delete_one_image_file(username, image_filename) :
    final_path = generate_image_fullpath(username, image_filename)
    logger.info('remove file: ' + final_path)
    if os.path.exists(final_path):
        os.remove(final_path)
    final_path = get_txtfilename_from_image(username, image_filename)
    if os.path.exists(final_path):
        os.remove(final_path)
