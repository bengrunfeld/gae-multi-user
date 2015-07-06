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
    "Models an individual todo title"
    title = ndb.StringProperty()
    time_stored = ndb.DateTimeProperty(auto_now_add=True)


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

        print user.user_id()

        template_data = {
            'username': user.nickname(),
        }

        template = JINJA_ENVIRONMENT.get_template('account.html')
        self.response.write(template.render(template_data))


class Logout(BaseHandler):
    """
    4. Logout from app and reset user login session 
    """

    def get(self):
        self.session['logged_in'] = False
        self.redirect(users.create_logout_url('/'))
        return
        

class GetAllTodos(webapp2.RequestHandler):
    """GET /: Retrieve all todos"""

    def get(self):
        try:
            qry = TodoModel.query().fetch()
            all_todos = serialize_data(qry)

            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write(json.dumps(all_todos, sort_keys=True, indent=4))
        except:
            # TODO: Improve this error 
            raise Exception("Error: could not complete request")            


class CreateTodo(webapp2.RequestHandler):
    """POST /: Create a single todo"""

    def post(self):
        try:
            new_todo = TodoModel(title = self.request.get('title')) 
            key = new_todo.put()

            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Successfully added new todo')
        except:
            raise Exception("Error: could not complete request")

app = webapp2.WSGIApplication([
   ('/sign-in', SignIn),
   ('/account', LoadAccount),
   ('/logout', Logout),
   ('/', GoToLoginPage),
], config=config)
