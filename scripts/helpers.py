# -*- coding: utf-8 -*-

from scripts import tabledef
from flask import session
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from requests.structures import CaseInsensitiveDict
import bcrypt
import os
from PIL import Image

root_path ='C:/Luo/Repos/TesseractOcrTraining/files'

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
    with session_scope() as s:
        user = s.query(tabledef.User).filter(tabledef.User.username.in_([username])).first()
        return user


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

def create_folder_if_not_exists(path_name) :
    #If folder doesn't exist, then create it
    if not os.path.isdir(path_name):
        os.makedirs(path_name)
        #print("created folder : ", path_name)


def list_folder_image_text_pair(username) :
    global root_path 
    final_path = os.path.join(root_path, username)
    create_folder_if_not_exists(final_path)
    list_of_files = os.listdir(final_path)
    if list_of_files is None :
        list_of_files=[]
    else :
        list_of_files.sort()
    
    hash_set = {v.lower():v for v in list_of_files }
    result =[]
    for one_file in list_of_files :
        if not one_file :
            continue 
        one_file_lower = one_file.lower()
        if one_file_lower.endswith('tif') or one_file_lower.endswith('png') :
            text_filename = one_file_lower +'.gt.txt'
            if text_filename in hash_set :
                result.append( (one_file, hash_set[text_filename]) )
            else :
                result.append( (one_file, '') )
    return result
   
def list_folder_result(username) :
    global root_path 
    final_path = os.path.join(root_path, username, 'results')
    create_folder_if_not_exists(final_path)
    list_of_files = os.listdir(final_path)
    if list_of_files is None :
        list_of_files=[]
    list_of_files.sort()
    return list_of_files
    

def save_image_file(username, fileitem)
    # check if the file has been uploaded
    try :
        if fileitem.filename:
            # strip the leading path from the file name
            fn = os.path.basename(fileitem.filename)
            fn_lower = fn.lower()
            final_filename = fn
            need_convert_image_file = False 
            if not  ( fn_lower.endswith('.png') or fn_lower.endswith('.tif') ) :
                final_filename +='.png'
                need_convert_image_file = True
            final_filename = os.path.join(root_path, username, final_filename)
           # open read and write the file into the server
            if need_convert_image_file :
                im = Image.open(fileitem.file)
                im.save(final_filename)
            else :
                open(final_filename, 'wb').write(fileitem.file.read())
        return
    except   Exception as e :
        return e

# return all current tesseract train data to begin with            
def get_all_template(username ) :
    template_path =final_filename = os.path.join(root_path, '../template')
    create_folder_if_not_exists(template_path)
    list_of_files = os.listdir(template_path)
    if list_of_files is None :
        list_of_files=[]
    list_of_files.sort()
    return list_of_files
    
def start_training_process(template) :
    template_path =  os.path.join(root_path, '../template')
    final_filename= os.path.join(template_path, template)
 
    if list_of_files is None :
        list_of_files=[]
    list_of_files.sort()