# import requirements needed
from flask import Flask, render_template, redirect, request
from utils import get_base_url
from flask import request as flask_request
import requests
import base64
import os
import shutil
from PIL import Image  

# setup the webserver
# port may need to be changed if there are multiple flask servers running on same server
port = 12345
base_url = get_base_url(port)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg'}
#clears uploads folder on flask app run
for filename in os.listdir(UPLOAD_FOLDER):
  file_path = os.path.join(UPLOAD_FOLDER, filename)
  try:
    if os.path.isfile(file_path) or os.path.islink(file_path):
      os.unlink(file_path)
    elif os.path.isdir(file_path):
      shutil.rmtree(file_path)
  except Exception as e:
    print('Failed to delete %s. Reason: %s' % (file_path, e))


#Model inferences
#Race
API_URL_RACE = "https://api-inference.huggingface.co/models/crangana/trained-race"
headers = {"Authorization": "Bearer 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"}


def query_race(filename):
  with open(filename, "rb") as f:
    data = f.read()
  response = requests.post(API_URL_RACE, headers=headers, data=data)
  return response.json()


#Age
API_URL_AGE = "https://api-inference.huggingface.co/models/crangana/trained-age"

def query_age(filename):
  with open(filename, "rb") as f:
    data = f.read()
  response = requests.post(API_URL_AGE, headers=headers, data=data)
  return response.json()


#Gender
API_URL_GENDER = "https://api-inference.huggingface.co/models/crangana/trained-gender"

def query_gender(filename):
  with open(filename, "rb") as f:
    data = f.read()
  response = requests.post(API_URL_GENDER, headers=headers, data=data)
  return response.json()

#Face detection inference
def face_det(image_path):
  with open(image_path, "rb") as image_file:    
    image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

  # print('open file ok')
  url = "https://detect.roboflow.com/face-det-npvna/1"
  params = {"api_key": "V0EgyW40xJS7sGZUm9SH"}
  
  headers = {"Content-Type": "application/x-www-form-urlencoded"}
  
  response = requests.post(url, params=params, data=image_base64, headers=headers)
  crop_data = response.json()
  print(crop_data)
  
  # Extract crop dimensions from JSON data
  width = crop_data["predictions"][0]["width"]
  height = crop_data["predictions"][0]["height"]
  x = crop_data["predictions"][0]["x"] - width/2
  y = crop_data["predictions"][0]["y"] - height/2

  image = Image.open(image_path)

  cropped_image = image.crop((x, y, x + width, y + height))
  
  # Save the cropped image
  cropped_image.save("static/uploads/cropped_image.jpg")

  print('ok')
  return "static/uploads/cropped_image.jpg"


#Get max values
def get_max_vals(results):
  max_score = 0
  max_label = None

  # Loop through the list of dictionaries
  for item in results:
    score = item['score']
    label = item['label']

    # Check if the current score is greater than the maximum score found so far
    if score > max_score:
      max_score = score
      max_label = label
  return max_score, max_label



if base_url == '/':
  app = Flask(__name__)
else:
  app = Flask(__name__, static_url_path=base_url + 'static')

# adds upload folder to base app directory
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.urandom(64)

# app.static_folder = 'uploads'


# set up the routes and logic for the webserver
@app.route(f'{base_url}')
def home():
  return render_template('index2.html')


def allowed_file(filename):
  return '.' in filename and \
         filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



@app.route(f'{base_url}', methods=['POST'])
def upload_file():
  try:
    if flask_request.method == 'POST':
      if 'file' not in flask_request.files:
        # print("reached to file found")
        return render_template('results.html', error_msg="Please upload a JPG or JPEG file. If the problem persists, please try again in a while.")

      file = flask_request.files['file']

      if file.filename == '':
        return redirect(flask_request.url)

      if file and allowed_file(file.filename):
        filename = 'user_input.jpg'
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # static/uploads/user_input.jpg
        print(filename)
        filename = 'static/uploads/' + filename

        # get_faces(filename)

        print(filename)
        crop_filename = face_det(filename)
        # print(to_print)
        
        results_race = query_race(crop_filename)
        results_gender = query_gender(crop_filename)
        results_age = query_age(crop_filename)
        # print(results_race)
        race_prob, race_pred = get_max_vals(results_race)
        age_prob, age_pred = get_max_vals(results_age)
        gen_prob, gen_pred = get_max_vals(results_gender)
        print(race_prob, race_pred)
        return render_template('results.html',
                               race_perc=round(race_prob, 2),
                               race=race_pred,
                               age_perc=round(age_prob, 2),
                               age=age_pred,
                               gen_prob=round(gen_prob, 2),
                               gender=gen_pred,
                               filename=filename)
      else:
        return render_template('results.html', error_msg="Please upload a JPG or JPEG file. If the problem persists, please try again in a while.")

  except:
    return render_template('results.html', error_msg="Please upload a JPG or JPEG file. If the problem persists, please try again in a while.")


@app.route(f'{base_url}/results')
def results():
  race_perc = request.args.get('race_perc')
  race = request.args.getlist('race')
  print(race_perc, race)
  return render_template('results.html', race=race, race_perc=race_perc)



if __name__ == '__main__':
  website_url = 'url'

  print(f'Try to open\n\n    https://{website_url}' + base_url + '\n\n')
  app.run(host='0.0.0.0', port=port, debug=True)

