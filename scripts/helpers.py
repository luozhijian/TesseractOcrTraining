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
training_in_process = False

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
    
def get_training_in_process():
    return training_in_process


def get_user():
    username = session['username']
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
    with session_scope() as s:
        user = s.query(tabledef.User).filter(tabledef.User.username.in_([username])).first()
        if user:
            return bcrypt.checkpw(password.encode('utf8'), user.password.encode('utf8'))
        else:
            return False


def username_taken(username):
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
    log_filename = 'log_' + datetime.utcnow().strftime('%Y%m%d_%H%M%S%f')
    return os.path.join(log_folder, log_filename +'.log')

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
            text_filename = get_txtfilename_only_from_image(one_file)
            if text_filename in hash_set :
                full_text_filename = os.path.join(final_path, text_filename)
                text_content = open(full_text_filename, 'r').read()
                result.append( (one_file, hash_set[text_filename], text_content) )
            else :
                result.append( (one_file, '', '') )
        elif  not ( one_file_lower.endswith('.gt.txt')  or one_file_lower.endswith('.lstmf')  or one_file_lower.endswith('.box') ) :
            result.append( (one_file, '', '') )
            
    return result
   
def list_folder_result(username, folder) :
    global root_path 
    final_path = generate_result_folder(username)
    create_folder_if_not_exists(final_path)
    list_of_files=[]
    for dir_, _, files in os.walk(final_path):
        for file_name in files:
            rel_dir = os.path.relpath(dir_, final_path)
            if not rel_dir  or rel_dir == '.' :   
                rel_file = file_name
            else :
                rel_file = os.path.join(rel_dir, file_name)
                
            list_of_files.append([urllib.parse.quote_plus(rel_file, safe='') , rel_file, folder])
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
    
def start_training_process(username, template) :
    training_in_process =True
    log_filename =''
    template_path =  os.path.join(root_path, '../template')
    final_templatename= os.path.join(template_path, template)
    image_folder  = generate_image_folder(username)
    
    processThread = Thread(target=start_training_action, args=(username, final_templatename, image_folder));
    processThread.start()
 
    
    
def start_training_action(username, templatename, image_folder) :
    global current_log_name,training_in_process
    try :
        log_folder = os.path.join(image_folder, 'log')
        create_folder_if_not_exists (log_folder)
        log_filename = 'log_' + datetime.utcnow().strftime('%Y%m%d_%H%M%S%f')
        current_log_name = os.path.join(log_folder, log_filename +'.log')
        print (current_log_name)
        logger.info(current_log_name)
        with open(current_log_name, 'a') as the_file:
            for index in range(200): 
                the_file.write(datetime.utcnow().strftime('%Y%m%d_%H%M%S%f') +'\n')
                the_file.flush()
                time.sleep(1.5)
    except Exception as e:
        print (e)
    finally :
        training_in_process =False 
        
    
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
