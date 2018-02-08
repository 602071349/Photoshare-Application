
# Some code adapted from 
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
from functools import reduce 
from collections import OrderedDict
import flask.ext.login as flask_login

#for image uploading
from werkzeug import secure_filename
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '0987123' #CHANGE THIS TO YOUR MYSQL PASSWORD
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users") 
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users") 
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd
	return user


'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out') 

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html') 

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register/", methods=['GET'])
def register():
	return render_template('improved_register.html', supress='True')  
	
@app.route("/register1/", methods=['GET'])	
def register1():
	return render_template('improved_register.html', supress='True',error="ERROR!Email already exists.") 

@app.route("/register/", methods=['POST'])
def register_user():
	try:
		email=request.form.get('email')
		password=request.form.get('password')
		first_name=request.form.get('firstname')
		last_name=request.form.get('lastname')
		date_of_birth=request.form.get('birthday')
		gender=request.form.get('gender')
		hometown=request.form.get('hometown')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print(cursor.execute("INSERT INTO Users (email, password,first_name,last_name,date_of_birth,gender,hometown) VALUES ('{0}', '{1}','{2}','{3}','{4}','{5}','{6}')".format(email, password,first_name,last_name,date_of_birth,gender,hometown)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!')
	else:
		print("email already exists")
		return flask.redirect(flask.url_for('register1'))

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]
	

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)): 
		#this means there are greater than zero entries with that email
		return False
	else:
		return True
		
def getlikeinfo(picture_id):
	cursor=conn.cursor()
	cursor.execute("SELECT COUNT(*) FROM likes WHERE picture_id='{0}'".format(picture_id))
	number=cursor.fetchone()
	cursor.execute("SELECT U.first_name,U.last_name FROM users U,likes L WHERE U.user_id = L.user_id AND L.picture_id='{0}'".format(picture_id))
	users=cursor.fetchall()
	result=[number]+[users]
	return result
#end login code

@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('hello.html', name=flask_login.current_user.id, message="Here's your profile")

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML 
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		album = request.form.get('album')
		photo_data = base64.standard_b64encode(imgfile.read()).decode('utf-8')
		cursor = conn.cursor()
		cursor.execute("Select album_id FROM Albums WHERE user_id='{0}' AND name='{1}'".format(uid,album))
		album_id=cursor.fetchone()[0]
		cursor.execute("INSERT INTO pictures (album_id,imgdata, user_id, caption) VALUES ('{0}','{1}', '{2}','{3}' )".format(album_id,photo_data,uid, caption))
		conn.commit()
		return render_template('hello.html', name=flask_login.current_user.id, message='Photo uploaded!', photos=getUsersPhotos(uid) )
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html')
#end photo uploading code 


#default page  
@app.route("/", methods=['GET'])
def hello():
	return render_template('hello.html', message='Welcome to Photoshare')


if __name__ == "__main__":
	#this is invoked when in the shell you run 
	#$ python app.py 
	app.run(port=5000, debug=True)

@app.route('/addfriend',methods=['GET','POST'])
@flask_login.login_required
def add_friend():
	if request.method =='POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		first_name=request.form.get('first_name')
		last_name=request.form.get('last_name')
		cursor=conn.cursor()
		cursor.execute("SELECT user_id FROM users WHERE first_name='{0}' AND last_name='{1}'".format(first_name,last_name))
		friend_id=cursor.fetchone()[0]
		cursor.execute("INSERT INTO user_friend(user_id,friend_id) VALUES ('{0}','{1}')".format(uid,friend_id))
		conn.commit()
		return render_template('hello.html',name=flask_login.current_user.id,message='Friend added!')
	else:
		return render_template('addfriend.html')
		
@app.route('/listfriends',methods=['GET'])
@flask_login.login_required
def list_friend():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor=conn.cursor()
	cursor.execute("SELECT A.first_name, A.last_name FROM users U,user_friend F, users A WHERE U.user_id=F.user_id AND F.friend_id=A.user_id AND U.user_id='{0}'".format(uid))
	friends=cursor.fetchall()
	return render_template('listfriends.html',friends=friends)

@app.route('/createalbum',methods=['GET','POST'])
@flask_login.login_required	
def create_album():
	if request.method=='POST':
		uid= getUserIdFromEmail(flask_login.current_user.id)
		album_name=request.form.get('name')
		creation_date=request.form.get('date')
		curosr=conn.cursor()
		cursor.execute("INSERT INTO albums(name,user_id,date_of_creation) VALUES ('{0}','{1}','{2}')".format(album_name,uid,creation_date))
		conn.commit()
		return render_template('hello.html',name=flask_login.current_user.id,message='Album added!')
	else:
		return render_template('createalbum.html')
		
@app.route('/delete',methods=['GET','POST'])
@flask_login.login_required	
def delete():
	if request.method=='POST':
		uid= getUserIdFromEmail(flask_login.current_user.id)
		caption=request.form.get('caption')
		cursor=conn.cursor()
		cursor.execute("DELETE FROM pictures WHERE user_id='{0}' AND caption='{1}'".format(uid,caption))
		conn.commit()
		return render_template('hello.html',name=flask_login.current_user.id,message='Photo deleted!')
	else:
		return render_template('delete.html')
		
@app.route('/remove',methods=['GET','POST'])
@flask_login.login_required	
def remove():
	if request.method=='POST':
		uid= getUserIdFromEmail(flask_login.current_user.id)
		name=request.form.get('name')
		cursor=conn.cursor()
		cursor.execute("SELECT album_id FROM albums WHERE name='{0}' AND user_id='{1}'".format(name,uid))
		album_id=cursor.fetchone()[0]
		cursor.execute("DELETE FROM pictures WHERE user_id='{0}' AND album_id='{1}'".format(uid,album_id))
		cursor.execute("DELETE FROM albums WHERE user_id='{0}' AND name='{1}'".format(uid,name))
		conn.commit()
		return render_template('hello.html',name=flask_login.current_user.id,message='Album deleted!')
	else:
		return render_template('remove.html')
		
@app.route('/browse',methods=['GET'])
def browse():
	cursor=conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM pictures ORDER BY picture_id")
	pictures=cursor.fetchall()
	return render_template('hello.html', message='Browse all the photos!', photos=pictures)
	
@app.route('/comment',methods=['POST'])
def comment():
	uid=-1
	if flask_login.current_user.is_authenticated:
		uid=getUserIdFromEmail(flask_login.current_user.id)
	comment=request.form.get('comment')
	date=request.form.get('date')
	picture_id=request.form.get('id')
	cursor=conn.cursor()
	cursor.execute("SELECT user_id FROM pictures WHERE picture_id='{0}'".format(picture_id))
	uid1=cursor.fetchone()[0]
	if uid==uid1:
		return render_template('hello.html',name=flask_login.current_user.id,message='Can not comment your own photos!')
	else:
		cursor.execute("INSERT INTO comments(text,user_id,picture_id,date_of_creation) VALUES('{0}','{1}','{2}','{3}')".format(comment,uid,picture_id,date))
		conn.commit()
		return render_template('hello.html',message='Comment Added!')
		
@app.route('/contribution',methods=['GET'])
def contribution():
	cursor=conn.cursor()
	cursor.execute("SELECT U.first_name,U.last_name,IFNULL(T1.number,0) FROM users U LEFT JOIN (SELECT user_id AS id,COUNT(*) AS number FROM comments GROUP BY user_id) AS T1 ON U.user_id =T1.id ORDER BY U.user_id ASC")
	lst=cursor.fetchall()
	cursor.execute("SELECT U.first_name,U.last_name,IFNULL(T1.number,0) FROM users U LEFT JOIN (SELECT user_id AS id,COUNT(*) AS number FROM pictures GROUP BY user_id) AS T1 ON U.user_id =T1.id ORDER BY U.user_id ASC")
	lst1=cursor.fetchall()
	lst=[(lst[i][0],lst[i][1],lst[i][2]+lst1[i][2]) for i in range(len(lst))]
	lst=sorted(lst, key=lambda x: x[2],reverse=True)
	result=lst[0:10]
	return render_template('contribution.html',lst=result)			
					
@app.route('/like',methods=['POST'])
@flask_login.login_required	
def like():
	uid=getUserIdFromEmail(flask_login.current_user.id)
	picture_id=request.form.get('id')
	cursor=conn.cursor()
	cursor.execute("INSERT INTO likes(user_id,picture_id) VALUES('{0}','{1}')".format(uid,picture_id))
	conn.commit()
	return render_template('hello.html',name=flask_login.current_user.id,message='Photo liked!')
	
@app.route('/listlikes',methods=['GET'])
def listlikes():
	cursor=conn.cursor()
	cursor.execute("SELECT picture_id,imgdata FROM pictures ORDER BY picture_id")
	result=[]
	lst=cursor.fetchall()
	for i in lst:
		likeinfo=getlikeinfo(i[0])
		lst1=[i]+likeinfo
		result+=[lst1]
	return render_template('listlikes.html',lst=result)
	
@app.route('/createtag',methods=['GET','POST'])
def createtag():
	if request.method=='POST':
		word=request.form.get('word')
		cursor=conn.cursor()
		cursor.execute("INSERT INTO tags(word) VALUES('{0}')".format(word))
		conn.commit()
		return render_template('hello.html',message='Tag created!')
	else:
		return render_template('createtag.html')
		
@app.route('/addtag',methods=['GET','POST'])
@flask_login.login_required	
def addtag():
	if request.method=='POST':
		uid=getUserIdFromEmail(flask_login.current_user.id)
		picture_caption=request.form.get('caption')
		word=request.form.get('word')
		cursor=conn.cursor()
		cursor.execute("SELECT picture_id FROM pictures WHERE user_id='{0}' AND caption='{1}'".format(uid,picture_caption))
		id=cursor.fetchone()[0]
		cursor.execute("INSERT INTO photo_tag(picture_id,word) VALUES ('{0}','{1}')".format(id,word))
		conn.commit()
		return render_template('hello.html',message='Tag added!')
	else:
		return render_template('addtag.html')
		
@app.route('/listbytag/<tag>',methods=['GET'])
@flask_login.login_required	
def listbytag(tag):
	uid=getUserIdFromEmail(flask_login.current_user.id)
	curosr=conn.cursor()
	cursor.execute("SELECT P.imgdata,P.picture_id,P.caption FROM pictures P,photo_tag A WHERE A.picture_id =P.picture_id AND A.word='{0}' AND P.user_id='{1}'".format(tag,uid))
	pictures=cursor.fetchall()
	return render_template('hello.html', message='Browse your photos of the tag!', photos=pictures)

@app.route('/listbytag1/<tag>',methods=['GET'])
def listbytag1(tag):
	cursor=conn.cursor()
	cursor.execute("SELECT P.imgdata,P.picture_id,P.caption FROM pictures P,photo_tag A WHERE A.picture_id=P.picture_id AND A.word='{0}'".format(tag))
	pictures=cursor.fetchall()
	return render_template('hello.html', message='Browse all photos of the tag!', photos=pictures)


	
@app.route('/viewbytag',methods=['GET'])
@flask_login.login_required	
def viewbytag():
		uid=getUserIdFromEmail(flask_login.current_user.id)
		cursor=conn.cursor()
		cursor.execute("SELECT A.word FROM pictures P,photo_tag A,users U WHERE A.picture_id =P.picture_id AND P.user_id=U.user_id AND P.user_id='{0}'".format(uid))
		tags=cursor.fetchall()
		return render_template('listtags.html',tags=tags)


@app.route('/viewpopulartag',methods=['GET'])		
def viewpopulartag():
	cursor=conn.cursor()
	cursor.execute("SELECT word FROM Photo_tag GROUP BY word ORDER BY COUNT(*) DESC")
	tags=cursor.fetchall()
	return render_template('listpopulartags.html',tags=tags)
	
@app.route('/search',methods=['GET','POST'])
def search():
	if request.method=='POST':
		word=request.form.get('word')
		word=word.split(' ')
		len1=len(word)
		lst=[]
		cursor=conn.cursor()
		for i in range(len1):
			cursor.execute("SELECT picture_id FROM Photo_tag WHERE word='{0}'".format(word[i]))
			tu=cursor.fetchall()
			tu=[x[0] for x in tu]
			lst+=[tu]
		lst=list(reduce(set.intersection, [set(x) for x in lst ]))
		lst1=[]
		for j in lst:
			cursor.execute("SELECT imgdata,picture_id,caption FROM pictures WHERE picture_id='{0}'".format(j))
			one=cursor.fetchone()
			lst1+=[one]
		return render_template('hello.html', message='Search results!', photos=lst1)
	else:
		return render_template('search.html')
		
@app.route('/yourphotos',methods=['GET'])
@flask_login.login_required	
def yourphotos():
	uid=getUserIdFromEmail(flask_login.current_user.id)
	cursor=conn.cursor()
	cursor.execute("SELECT imgdata,picture_id,caption FROM pictures WHERE user_id='{0}'".format(uid))
	pictures=cursor.fetchall()
	return render_template('hello.html',message='Browse your own photos',photos=pictures)

@app.route('/youralbums',methods=['GET'])
@flask_login.login_required	
def youralbums():
	uid=getUserIdFromEmail(flask_login.current_user.id)
	cursor=conn.cursor()
	cursor.execute("SELECT name FROM albums WHERE user_id='{0}'".format(uid))
	albums=cursor.fetchall()
	return render_template('youralbums.html',albums=albums)
	
@app.route('/viewbyalbum',methods=['GET','POST'])
@flask_login.login_required	
def viewbyalbum():
	if request.method=='POST':
		uid=getUserIdFromEmail(flask_login.current_user.id)
		name=request.form.get('name')
		cursor=conn.cursor()
		cursor.execute("SELECT imgdata,picture_id,caption FROM pictures P,albums A WHERE P.album_id = A.album_id AND A.name='{0}' AND P.user_id='{1}'".format(name,uid))
		pictures=cursor.fetchall()
		return render_template('hello.html',message='Browse your photos of the album',photos=pictures)
	else:
		return render_template('viewbyalbum.html')
		
@app.route('/viewcomments',methods=['GET','POST'])	
def viewcomments():
	if request.method=='POST':
		picture_id=request.form.get('id')
		cursor=conn.cursor()
		cursor.execute("SELECT U.first_name,U.last_name,C.text,C.date_of_creation FROM users U,comments C WHERE C.user_id=U.user_id AND C.picture_id='{0}'".format(picture_id))
		comments=cursor.fetchall()
		cursor.execute("SELECT text,date_of_creation FROM comments WHERE user_id=-1 AND picture_id='{0}'".format(picture_id))
		guest_comments=cursor.fetchall()
		return render_template('viewcomments.html',comments=comments,guest_comments=guest_comments)
	else:
		return render_template('comments.html')
		
@app.route('/recommendations',methods=['GET'])
@flask_login.login_required	
def recommendations():
	uid=getUserIdFromEmail(flask_login.current_user.id)
	cursor=conn.cursor()
	cursor.execute("SELECT T.word FROM photo_tag T, pictures P WHERE P.picture_id=T.picture_id AND P.user_id='{0}' GROUP BY T.word ORDER BY COUNT(*) DESC".format(uid))
	tags=cursor.fetchall()
	lst=[x[0] for x in tags]
	lst=lst[0:5]
	lst1=[]
	for i in lst:
		cursor.execute("SELECT P.picture_id,P.user_id FROM pictures P, photo_tag T WHERE P.picture_id=T.picture_id AND T.word='{0}'".format(i))
		pictures=cursor.fetchall()
		pictures=[x[0]for x in pictures if x[1]!=uid]
		lst1+=pictures
	lst1=list(OrderedDict.fromkeys(lst1))
	lst2=[]
	for j in lst1:
		cursor.execute("SELECT imgdata,picture_id,caption FROM pictures WHERE picture_id='{0}'".format(j))
		one=cursor.fetchone()
		lst2+=[one]
	return render_template('hello.html', message='Recommendations!', photos=lst2)
		
	
	

		
	

	
				   
				   

		
		
		
		
		
		
		
		
