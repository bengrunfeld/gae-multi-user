"""
The handlers below are triggered by routes.py

They execute commands that retrieve, store, update and delete resources.
"""

import json
import webapp2
import datetime
import jinja2
import os

from google.appengine.ext import ndb
from google.appengine.api import users
from webapp2_extras import sessions

TEMPLATE_DIR = 'templates'
TEMPLATE_SUFFIX = '.html'

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'that-looks-uncomfortably-large',
}


class TodoModel(ndb.Model):
    "Models a todo title"
    title = ndb.StringProperty()
    time_stored = ndb.DateTimeProperty(auto_now_add=True)


class UserTodo(ndb.Model):
    "Models a todo for an individual User"
    name = ndb.StringProperty()
    todo = ndb.StructuredProperty(TodoModel, repeated=True)


def build_new_dict(data):
    """Build a new dict so that the data can be JSON serializable"""

    result = data.to_dict()
    record = {}

    # Populate the new dict with JSON serializiable values
    for key in result.iterkeys():
        if isinstance(result[key], datetime.datetime):
            record[key] = result[key].isoformat()
            continue
        record[key] = result[key]
    
    # Add the key so that we have a reference to the record
    record['key'] = data.key.id()

    return record


def serialize_data(qry):
    """serialize ndb return data so that we can convert it to JSON"""
    
    # check if qry is a list (multiple records) or not (single record)
    data = []
    
    if type(qry) != list: 
        record = build_new_dict(qry) 
        return record

    for q in qry:
        data.append(build_new_dict(q))

    return data 


class BaseHandler(webapp2.RequestHandler):
    """
    Set up sessions and perform template renders
    """

    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)

        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key.
        return self.session_store.get_session()


class GoToLoginPage(webapp2.RequestHandler):
    """
    1. Load the login page 
    """

    def get(self):
        template = JINJA_ENVIRONMENT.get_template('login.html')
        self.response.write(template.render())


class SignIn(BaseHandler):
    """
    2. Log the User in using Google Accounts 
    """

    def get(self):
        if self.session.get('logged_in'):
            # User is logged in, proceed to account
            self.redirect('/account') 
            return

        # Checks for active Google account session
        user = users.get_current_user()

        if user:
            # Redirect to Accounts page
            self.session['logged_in'] = True
            self.redirect('/account')
        else:
            self.session['logged_in'] = False
            self.redirect(users.create_login_url(self.request.uri))


class LoadAccount(BaseHandler):
    """
    3. Render the front end of the app, with User data
    """

    def get(self):
        # Check if User is logged in. If not, send to auth

        if not self.session.get('logged_in'):
            self.redirect('/sign-in')
            return

        # Checks for active Google account session
        user = users.get_current_user()

        # Check if User has their own data object specifically for them
        # if they don't, create it for them
        userHasOwnData = UserTodo.get_by_id(user.user_id())
        
        if userHasOwnData == None:
            # Make new account for User
            new_user = UserTodo(
                   key = ndb.Key('UserTodo', user.user_id()),
                   name = user.nickname(),
            ) 
            logKey = new_user.put()
        

        # Grab data from the data store
        qry = UserTodo.get_by_id(user.user_id())
        todos = serialize_data(qry)

        # put titles into a list so that Jinja can use it
        results = []

        for todo in todos['todo']:
            results.append(todo['title'])

        template_data = {
            'username': user.nickname(),
            'todos': results,
        }

        template = JINJA_ENVIRONMENT.get_template('account.html')
        self.response.write(template.render(template_data))


class CreateTodo(BaseHandler):
    """POST /: Create a single todo"""

    def post(self):

        # Checks for active Google account session
        user = users.get_current_user()

        target = UserTodo.get_by_id(user.user_id())
        target.todo.append(TodoModel(title = self.request.get('title')))
        target.put()

        self.redirect('/account')


class Logout(BaseHandler):
    """
    4. Logout from app and reset user login session 
    """

    def get(self):
        self.session['logged_in'] = False
        self.redirect(users.create_logout_url('/'))
        return
 

app = webapp2.WSGIApplication([
   ('/sign-in', SignIn),
   ('/account', LoadAccount),
   ('/logout', Logout),
   ('/post', CreateTodo),
   ('/', GoToLoginPage),
], config=config)
