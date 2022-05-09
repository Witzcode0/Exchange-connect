# README #

### Contributing Guidelines ###

* Fork repo
* Create pull requests
* Add manual tests for all functionality to tests folder as simple txt files
* Add swagger (https://swagger.io/docs/specification/2-0/basic-structure/) docs for each api created, see below for guidelines

### Coding Guidelines ###

* Keep your code readable
* Follow pep8 conventions, including but not limited to the following:
    1. 80 character lines limit
    2. double newlines between classes, and functions
    3. single newlines between methods of classes

### Swagger Guidelines ###

* use `swag_from` decorator
* create a folder within the package with name: "swagger_docs"
* add swagger spec for each endpoint in a separate file
* use these files in the `swag_from` call
* for schemas, models, to easily generate them:
    1. in console, import `aspec`, import required schema
    2. generate the spec, and convert the generated dict to json/yaml
    3. edit to correct yaml
    4. copy the "definition" all required files

```python
# sample code
from app import aspec, create_app
# create an app to avoid all import problems
app = create_app('config')
# use a request context
with app.test_request_context():
    # import required schema
    from app.resources.events.schemas import EventSchema
    # generate the spec
    aspec.definition('Event', schema=EventSchema)
# convert to json
import json
import yaml
dump_dict = json.dumps(aspec.to_dict(), sort_keys=True)
# covert into yml
with open('app/resources/events/swagger_docs/definitions/events_defs.yml',
          'w') as yaml_file:
    yaml.safe_dump(json.loads(dump_dict), yaml_file, default_flow_style=False)
```

* check samples in "auth" api, and "registration_request" api
* check generated ui at: http://localhost:5000/apidocs/

### Local Development ###

TODO: Add more

#### External Dependencies ####

Ubuntu:  
`apt-get install postgresql postgresql-contrib rabbitmq-server librabbitmq4 build-essential libssl-dev libffi-dev python3-dev freetds-dev libmagickwand-dev`

Mac:  
use homebrew for the above, minimum required:  
`brew install freetds@0.91 freetype imagemagick@6 libmagic`

#### DB Setup ####

After installing application and its dependencies:

1. Update the local configurations
2. Create the database in postgres: `CREATE DATABASE bse_corporate_solution;`
3. Create the tables with command: `python commands/manage.py setup_db`
4. Setup roles, default admin account, and default user with command: `python commands/manage.py setup_default_db -eml <email> -pwd <pwd> -fn <name> -ln <name>`
