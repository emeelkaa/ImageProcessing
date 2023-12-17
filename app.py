from flask import Flask, flash, request, redirect, url_for, render_template, send_file
import os
from werkzeug.utils import secure_filename
from PIL import Image
import json

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads/'
app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def adjust_brightness_contrast(image, brightness_factor, contrast_factor):
    from PIL import ImageEnhance

    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(brightness_factor)

    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(contrast_factor)

    return image

def save_image(image, filename):
    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

def crop_and_save_image(image, crop_data, filename_prefix):
    x, y, width, height = map(int, (crop_data['x'], crop_data['y'], crop_data['width'], crop_data['height']))
    cropped_img = image.crop((x, y, x + width, y + height))
    cropped_filename = f"{filename_prefix}_cropped.png"
    cropped_path = os.path.join(app.config['UPLOAD_FOLDER'], cropped_filename)
    save_image(cropped_img, cropped_filename)
    return cropped_filename

def crop_image_into_squares(image, num_squares, filename_prefix):
    square_width = image.width // num_squares
    square_height = image.height // num_squares
    cropped_images = []

    for i in range(num_squares):
        for j in range(num_squares):
            left = i * square_width
            upper = j * square_height
            right = (i + 1) * square_width
            lower = (j + 1) * square_height

            square = image.crop((left, upper, right, lower))
            square_filename = f"{filename_prefix}_square_{i}_{j}.png"
            save_image(square, square_filename)
            cropped_images.append(square_filename)

    return cropped_images

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('No image selected for uploading')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        img = Image.open(file)
        aspect_ratio = img.width / img.height
        new_width = 500
        new_height = int(500 / aspect_ratio) if aspect_ratio >= 1 else 500
        img = img.resize((new_width, new_height))
        save_image(img, filename)

        flash('Image successfully uploaded and displayed below')
        return render_template('index.html', filename=filename)
    else:
        flash('Allowed image types are - png, jpg, jpeg, gif')
        return redirect(request.url)

@app.route('/display/<filename>')
def display_image(filename):
    return redirect(url_for('static', filename=f'uploads/{filename}'), code=301)

@app.route('/crop', methods=['POST'])
def crop_image():
    num_squares = int(request.form['num_squares'])
    filename = request.form.get('filename')
    brightness_factor = float(request.form.get('brightness', 1.0))
    contrast_factor = float(request.form.get('contrast', 1.0))
    custom_cropping_data = request.form.get('custom_cropping_data')
    crop_type = request.form.get('custom_crop_type')

    if not filename:
        flash('Filename not provided for cropping')
        return redirect(url_for('index'))

    original_img = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    adjusted_img = adjust_brightness_contrast(original_img, brightness_factor, contrast_factor)

    if crop_type == 'custom' and custom_cropping_data:
        custom_cropping_data = json.loads(custom_cropping_data)
        custom_cropped_filename = crop_and_save_image(adjusted_img, custom_cropping_data, filename)
        flash('Image successfully custom cropped')
        return render_template('index.html', filename=filename, custom_cropped_filename=custom_cropped_filename)

    cropped_images = crop_image_into_squares(adjusted_img, num_squares, filename)
    flash(f'Image successfully cropped into {num_squares} x {num_squares} squares with adjusted brightness and contrast')
    return render_template('index.html', filename=filename, cropped_images=cropped_images, num_squares=num_squares)

@app.route('/download/<filename>')
def download_square(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

if __name__ == "__main__":
    app.run()
