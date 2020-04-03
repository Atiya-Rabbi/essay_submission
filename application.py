import os

from flask import Flask, session, render_template, request, redirect, flash
from flask_session import Session
from flask_bcrypt import Bcrypt
from helpers import login_required
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/logout")
def logout():
    """ Log user out """

    # Forget any user ID
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/student", methods=["GET","POST"], endpoint='student')
@login_required
def student():
	if request.method == "POST":
		topic_id = request.form.get("select_topic")
		username = session["username"]
		db.execute("INSERT INTO stu_essay (username, topic_id) VALUES ( :username, :topic_id)",{ "username": username, "topic_id": topic_id })
		db.commit()
		essay_content = request.form.get("essay_content")
		print(essay_content)
		print(topic_id)
		directory = username
		parent_dir = "essays/"
		path = os.path.join(parent_dir, directory)
		try:
			os.mkdir(path)
		except FileExistsError:
			print("Directory already exists")
		
		print("session")
		

		file = open("essays/"+directory+"/"+topic_id+".txt", 'w+')
		file.write(topic_id+"\n")
		file.write(essay_content+"\n")
		file.close()
		flash('Essay submitted')
	topics = db.execute("SELECT * FROM topics").fetchall()
	return render_template("student.html", topics=topics)

@app.route("/teacher", methods=["GET", "POST"] ,endpoint='teacher')
@login_required
def teacher():
	if request.method=="POST":
		rows = db.execute("SELECT * FROM stu_essay").fetchall()
		essays=[]
		for row in rows:
			print(row)
			f= open("essays/"+str(row[1])+"/"+str(row[2])+".txt")
			file_contents=f.read()
			essays.append(file_contents)
			f.close()
		topics = db.execute("SELECT * FROM topics")
		return render_template("evaluate.html", essays=essays, topics=topics)
	return render_template("teacher.html")


@app.route("/", methods=["GET", "POST"])
def login():
	""" Log user in """
	# Forget any user_id
	session.clear()
	if request.method=="POST":
		username = request.form.get("username")
		password = request.form.get("password")
		userrole = request.form.get("userrole")
		print(userrole)
		if userrole == "student":
			rows = db.execute("SELECT * FROM student WHERE username = :username", {"username": username})
			result = rows.fetchone()
			print(str(result))
			# Ensure username exists and password is correct
			if result == None or not check_password_hash(result[3], request.form.get("password")):
				return render_template("error.html", message="invalid username and/or password")
			# Remember which user has logged in
			session["username"] = result[2]
			return redirect("/student")

		elif userrole == "teacher":
			rows = db.execute("SELECT * FROM teacher WHERE username = :username", {"username": username})
			result = rows.fetchone()
			print(str(result))
			# Ensure username exists and password is correct
			if result == None or not check_password_hash(result[3], request.form.get("password")):
				return render_template("error.html", message="invalid username and/or password")
			# Remember which user has logged in
			session["username"] = result[2]
			return redirect("/teacher")
			
	return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
	""" Register user """

	# Forget any user_id
	session.clear()

	# User reached route via POST (as by submitting a form via POST)
	if request.method == "POST":

		password = request.form.get("password")
		repassword = request.form.get("repassword")
		#check again if passwords match or not
		if(password!=repassword):
			return render_template("error.html", message="passwords do not match")

		#hashing password
		pw_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
		print("the type")
		print(type(pw_hash))
		fullname = request.form.get("fullname")
		username = request.form.get("username")
		userrole = request.form.get("userrole")
		print(userrole)
		if userrole == "student":
			if db.execute("SELECT username FROM student WHERE username=:username", {"username": username}).rowcount != 0:
				return render_template("error.html",message="username already exists")
			db.execute("INSERT INTO student (fullname, username, password) VALUES (:fullname, :username, :password)",{"fullname": fullname, "username": username, "password": pw_hash})
			db.commit()
		elif userrole == "teacher":
			if db.execute("SELECT username FROM teacher WHERE username=:username", {"username": username}).rowcount != 0:
				return render_template("error.html", message="username already exists")
			db.execute("INSERT INTO teacher (fullname, username, password) VALUES (:fullname, :username, :password)",{"fullname": fullname, "username": username, "password": pw_hash})
			db.commit()
		return render_template("login.html")
	return render_template("signup.html")

@app.route("/viewlist/<int:view>", methods=["GET", "POST"])
def viewlist(view):
	if request.method == "POST":
		list_filter = request.form.get("list_filter")
		print(view)
		print(list_filter)

		if view == 1:
			listofname = []
			if list_filter == "alphabetic":
				rows = db.execute("SELECT fullname FROM student").fetchall()
				for row in rows:
					listofname.append(row)
				print(listofname)
				listofname.sort()
				print(listofname)
			elif list_filter == "topicwise":
				rows = db.execute("SELECT * FROM topics").fetchall()
				print(rows)
				for row in rows:
					listofname.append(row[1])
					users = db.execute("SELECT student.fullname FROM student INNER JOIN stu_essay ON (student.username = stu_essay.username) AND (stu_essay.topic_id = :topic_id)",{"topic_id": row[0]}).fetchall()
					listofname.append(users)
			return render_template("viewlist.html",rows=listofname)
		elif view == 2:
			rows = db.execute("SELECT * FROM stu_essay").fetchall()
			essays=[]
			if list_filter == "studentwise":
				for row in rows:
					essays.append(str(row[1]))
					f= open("essays/"+str(row[1])+"/"+str(row[2])+".txt")
					file_contents=f.read()
					essays.append(file_contents)
					f.close()
			elif list_filter == "topicwise":
				for row in rows:
					f= open("essays/"+str(row[1])+"/"+str(row[2])+".txt")
					file_contents=f.read()
					essays.append(file_contents)
					f.close()

			topics = db.execute("SELECT * FROM topics")
			return render_template("evaluate.html", essays=essays, topics=topics)



	return redirect("/teacher")


@app.route("/topiclist", methods=["GET", "POST"])
def topiclist():
	if request.method=="POST":
		newtopic = request.form.get("newtopic")
		db.execute("INSERT INTO topics (topic_name) VALUES (:topic_name)",{"topic_name": newtopic})
		db.commit()

		alltopics = db.execute("SELECT topic_name FROM topics").fetchall()
		return render_template("topiclist.html", alltopics=alltopics)
	return redirect("/teacher")
