#Preparing to run segmentation API

#To make certs needs to execute that
#openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

#Another need to install python-dotenv package
#pip install python-dotenv

#http://192.168.77.212:8080/make_segmentation
# API short review
# / - get static content from 
# /dl_api/1.0/upload_src_img - upload source image
# /static/segmentations/sources/<filename> - show source image for segmentation
# /static/segmentations/result/<filename> - отображение сегментированных файлов
# /dl_api/1.0/segmentation/<filename> - run segmentaion process

import os
from flask import Flask, request, send_from_directory, Response, render_template, redirect, url_for, jsonify, make_response
from werkzeug.utils import secure_filename
from model import segmentation
from pathlib import Path
 
SVC_MODE = 'PROD'
UPLOAD_FOLDER = 'source_images'
RESULT_FOLDER = 'result_images'
ALLOWED_EXTENSIONS = set(['jpg', 'jpeg'])

# Set the project root directory as the static folder, you can set others.
#	static_url_path='' removes any preceding path from the URL (i.e. the default /static).
#	static_folder='web/static' to serve any files found in the folder web/static as static files.
#	template_folder='web/templates' similarly, this changes the templates folder.
   
app = Flask(__name__,
			static_url_path='/', 
			static_folder='build',
			template_folder='templates')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER
		
def _build_cors_prelight_response():
	response = make_response()
	response.headers.add('Access-Control-Allow-Origin', '*')
	response.headers.add('Access-Control-Allow-Headers', '*')
	response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
	return response
	
def _corsify_actual_response(response):
	response.headers.add("Access-Control-Allow-Origin", "*")
	return response
	
def resp(code, data):
	return Response(
		status=code,
		mimetype="application/json",
		response=jsonify(data)
	)
	
def allowed_file(filename):
	return '.' in filename and \
		str(filename.rsplit('.', 1)[1]).lower() in ALLOWED_EXTENSIONS
		
#Send static files (compiled react app)
@app.route('/')
def root():
	return app.send_static_file('index.html')

#Upload source image
@app.route('/dl_api/1.0/upload_src_img', methods=['POST','OPTIONS'])
def upload_img():
	if request.method == "OPTIONS": # CORS preflight
		return _build_cors_prelight_response()
	elif request.method == 'POST':
		#request.files = <FileStorage: 'Tulips.jpg' ('image/jpeg')>
		print('загрузка через API')
		file = request.files['file']
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			msg = {"message": "image was uploaded","code": "0","file_name": url_for('uploaded_file', filename=filename)}
			return _corsify_actual_response(jsonify(msg))
		else:
			return _corsify_actual_response(resp(406, {"server error": "invalid file format, please use .jpg"}))
	return _corsify_actual_response(resp(400, {"server error": "file uploading error"}))

#Show source image for segmentation
@app.route('/static/segmentations/sources/<filename>')
def uploaded_file(filename):
	return send_from_directory(app.config['UPLOAD_FOLDER'],filename)
	
#Run segmentaion process
@app.route('/dl_api/1.0/segmentation/<filename>', methods=['GET'])
def segmentation_run(filename):
	if filename and allowed_file(filename):
		source_filename = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
		dest_filename = os.path.join(app.config['RESULT_FOLDER'], secure_filename(filename))
		try:
			print('Run segmentaion process [' + source_filename + '] ...')
			segmentation_proc(source_filename, dest_filename, SVC_MODE)
			print('Segmentaion [' + dest_filename + '] done')
			msg = {
				"message": "segmendation done",
				"code": "0",
				"res_file_name": os.path.basename(dest_filename),
				"res_file_url": url_for('segmented_files', filename=os.path.basename(dest_filename)),
			}
			return _corsify_actual_response(jsonify(msg))		
		except Exception as ex:
			print('Segmentaion [' + dest_filename + '] ERROR ' + str(ex))
			return _corsify_actual_response(resp(406, {"segmentation error": "segmentation failure"}))

	return _corsify_actual_response(resp(400, {"server error": "file segmentation error"}))
	
#Show segmentation result file
@app.route('/static/segmentations/result/<filename>')
def segmented_files(filename):
	return send_from_directory(app.config['RESULT_FOLDER'],filename)	

#Show last 10 segmentations results
@app.route('/dl_api/1.0/last_segmentations')
def last_segmented_files():
	result_files_count = 7
	result_files = list(Path(RESULT_FOLDER).rglob('*.jpg'))
	result_files.sort(key=lambda x: os.path.getmtime(x))
	files = []
	for i in result_files[:-result_files_count:-1]:
		files.append({"src_file_url": url_for('uploaded_file'  , filename=i.name) ,
					  "res_file_url": url_for('segmented_files', filename=i.name)  })
	msg = {
		"message": "segmendation result set",
		"code": "0",
		"segmented_files": files
	}
	return _corsify_actual_response(jsonify(msg))	
	
	
#-------------------------------------------------------------------------------
#TEST LOCAL PAGES

#Source file upload form
@app.route('/upload_image', methods=['GET', 'POST'])
def upload_file():
	if request.method == 'POST':
		file = request.files['file']
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			return redirect(url_for('uploaded_file', filename=filename))
	return render_template('upload_form_template.html')

#Load source files and run segmentation
@app.route('/make_segmentation', methods=['GET', 'POST'])
def make_segmentation():
	if request.method == 'POST':
		file = request.files['file']
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			source_filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
			dest_filename = os.path.join(app.config['RESULT_FOLDER'], secure_filename(filename))
			
			try:
				print('Run segmentaion process [' + source_filename + '] ...')
				segmentation_proc(source_filename, dest_filename, SVC_MODE)
				print('Segmentaion [' + dest_filename + '] done')
			except Exception as ex:
				print('Segmentaion [' + dest_filename + '] ERROR ' + str(ex))
				return _corsify_actual_response(resp(406, {"segmentation error": "segmentation failure"}))
				
			return redirect(url_for('segmented_files', filename=filename))
	return render_template('segmentation_form_template.html')

def segmentation_proc(source_filename, dest_filename, mode):
	if mode == 'TEST':
		segmentation_stub(source_filename, dest_filename)
	else:
		segmentation(source_filename, dest_filename)
		
	
def segmentation_stub(source_filename, dest_filename):
	import shutil
	import time
	shutil.copyfile(source_filename, dest_filename)
	time.sleep(5)
	
if __name__ == "__main__":
	app.run()