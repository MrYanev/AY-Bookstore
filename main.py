from flask import Flask
from markupsafe import escape
from flask import url_for, render_template, jsonify, request, json, Response
from flask import redirect, make_response, session, abort, g
from http import HTTPStatus
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_script import Manager
from flask_uploads import UploadSet, configure_uploads, IMAGES
from werkzeug.utils import secure_filename
from werkzeug.datastructures import  FileStorage
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, DateField, FloatField, HiddenField
from flask_wtf.file import FileField, FileAllowed
import sqlite3


app = Flask(__name__)
photos = UploadSet('photos', IMAGES)

UPLOAD_FOLDER = 'AYBookstore/static/images/'
ALLOWED_EXTENTIONS = {'png', 'jpeg', 'jpg', }
#Defining a folder to store all the uploaded pictures and the allowed extentions

app.config['UPLOADED_PHOTOS_DEST'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'AB554BB4BD95FE73693A1C987FDBF'
#App configuration 

configure_uploads(app, photos)

db= SQLAlchemy(app)
migrate = Migrate(app, db)
#Setting up the database

manager = Manager(app)
manager.add_command('db', Migrate)

class Books(db.Model):
	isbn = db.Column(db.Integer, primary_key = True)
	name = db.Column(db.String(100), unique = True)
	author = db.Column(db.String(50))
	public_date = db.Column(db.Date)
	description = db.Column(db.String(1000))
	cover_photo = db.Column(db.String(100))
	trade_price = db.Column(db.Integer)
	retail_price = db.Column(db.Integer)
	quantity = db.Column(db.Integer)
#Creating class Books as a dataabse to store the book information
	

class AddBooks(FlaskForm):
	isbn = IntegerField('ISBN')
	name = StringField('Name')
	author = StringField('Author')
	public_date = DateField('Public Date')
	description = TextAreaField('Description')
	cover_photo = FileField('Cover Photo')
	trade_price = FloatField('Trade Price')
	retail_price = FloatField('Retail Price')
	quantity = IntegerField('Quantity')	
#Add form to add new books to the DB
	
class AddToCart():
	isbn = HiddenField('ISBN')
#Class AddToCart has a hidden field to pass the ISBN to the cart when adding an item

class User:
	def __init__(self, username, password):
		self.username = username
		self.password = password

		
users = []
users.append(User(username = 'customer1', password = 'p455w0rd'))
users.append(User(username = 'customer2', password = 'p455w0rd'))
users.append(User(username = 'admin', password = 'p455w0rd'))
#A list with the usernames and passwords for login


@app.before_request
def before_request():
	if 'user_name' in session:
		user = [x for x in users if x.username == session['user_name']][0]
		g.user = user
#A function to check if the username is in the session 
		
@app.route('/')
@app.route('/index')
def index():
	books = Books.query.all()
	
	return render_template("index.html", books = books)
#A function to render the home page template it also loads all the info from the database so it can be displayed
	
@app.route('/login', methods = ["POST", "GET"])
def login():
	if request.method == "POST":
		session.pop('user_name', None)
		
		username = request.form['username']
		password = request.form['password']
		
		user = [x for x in users if x.username == username][0]
		if user.username == 'admin' and user.password == password:
			return redirect(url_for('instock'))
		elif user and user.password == password:
			session['user_name'] = user.username
			return redirect(url_for('profile'))
		
		return redirect(url_for('register'))
	
	return render_template('login.html')
#Login function receives the information passed from the login form and it checks if the username and the password matches the ones in the list
#Redirecting to the instock page if the user logs in with the admin profile

@app.route('/register', methods = ["POST", "GET"])
def register():
	if request.method == 'PSOT':
		return do_registration(request.form['username'], request.form['password'])
	else:
		return show_registration_form()

	
def show_registration_form():
	return render_template('register.html', page=url_for('register'))

def do_registration(u, p):
	con = sqlite3.connect('registred_users.db')
	try:
		con.execute('CREATE TABLE users (name TEXT, pwd TEXT)')
		print ('Table created successfully');
	except:
		pass
	
	con.close()
	
	con = sqlite3.connect('registred_users.db')
	con.execute("INSERT INTO users values (?, ?);", (u, p))
	con.commit()
	con.close()
	
	return show_login_form()
#Register function to create new profiles they are stored in a different place than the main ones as its and extra function

@app.route('/profile')
def profile():
	if not g.user:
		return redirect(url_for('login'))
	
	return render_template('profile.html')
#A function to redirect the user to a basic 'profile' page

@app.route('/add', methods=['GET', 'POST'])
def add():
	form = AddBooks()
	
	if form.validate_on_submit():
		image_url = photos.url(photos.save(form.cover_photo.data)) #Generates the URL for the image
		
		new_book = Books(name = form.name.data, isbn = form.isbn.data, author = form.author.data,
						public_date = form.public_date.data, cover_photo = image_url,
						trade_price = form.trade_price.data, retail_price = form.retail_price.data,
						quantity = form.quantity.data)
		db.session.add(new_book)
		db.session.commit()
		
	return render_template('addbook.html', admin = True, form = form)
#This is the function for the add form where the admin can add new books to the databes
#it receives the information form the add book form and stores it in the databes it has admin=True so it can be accessed only by the admin 


@app.route('/instock')
def instock():
	books = Books.query.all()
	form = AddToCart()
	
	return render_template('instock.html', books = books, admin = True, form = form)
#Renders the instock page again only visible for the admin

@app.route('/cart')
def cart():
	books = []
	delnum = 0
	cart_total = 0
	
	for item in session['cart']:
		book = Books.query.filter_by(isbn=item['isbn']).first()
		
		quantity = int(item['quantity'])
		total = quantity * book.retail_price
		cart_total += total
		
		books.append({ 'isbn' : book.isbn, 'name' : book.name, 'price' : book.retail_price, 'cover_photo' : book.cover_photo, 'quantity' : quantity, 'total' : total, 'delnum' : delnum })
		delnum += 1
	
	return render_template('cart.html', books = books, cart_total=cart_total)
#The cart function creates an empty list or takes one from the session so whenever the user clicks add button the book gets appended to it

@app.route('/pop-cart/<delnum>')
def pop_cart(delnum):
	del session['cart'][int(delnum)]
	session.modified = True
	return redirect(url_for('cart'))

@app.route('/add-to-cart/<isbn>')
def add_to_cart(isbn):
	if 'cart' not in session:
		session['cart'] = []
		
	session['cart'].append({ 'isbn' : isbn, 'quantity' : 1 })
	session.modified = True
	
	return redirect(url_for('index'))
#This function passes the isbn to the cart 