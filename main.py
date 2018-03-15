#!/usr/bin/env python
import sys
import argparse
import tensorflow as tf
import io
from model import OpenNsfwModel, InputType
import flask
from PIL import Image
import numpy as np
import skimage
import skimage.io
from io import BytesIO

model_weights_path = 'data/open_nsfw-weights.npy'
model = OpenNsfwModel()

VGG_MEAN = [104, 117, 123]

img_width, img_height = 224, 224

app = flask.Flask(__name__)

def prepare_image(image):
    H, W, _ = image.shape
    h, w = (img_width, img_height)

    h_off = max((H - h) // 2, 0)
    w_off = max((W - w) // 2, 0)
    image = image[h_off:h_off + h, w_off:w_off + w, :]

    image = image[:, :, :: -1]

    image = image.astype(np.float32, copy=False)
    image = image * 255.0
    image -= np.array(VGG_MEAN, dtype=np.float32)

    image = np.expand_dims(image, axis=0)
    return image


@app.route("/predict", methods=["POST"])
def predict():
    if flask.request.method == "POST":
        if flask.request.files.get("image"):

            image = flask.request.files["image"].read()
            im = Image.open(io.BytesIO(image))

            if im.mode != "RGB":
                im = im.convert('RGB')

            imr = im.resize((256, 256), resample=Image.BILINEAR)

            fh_im = io.BytesIO()
            imr.save(fh_im, format='JPEG')
            fh_im.seek(0)

            image = (skimage.img_as_float(skimage.io.imread(fh_im, as_grey=False))
                            .astype(np.float32))

            final = prepare_image(image)

            
            tf.reset_default_graph()
            with tf.Session() as sess:
                
                input_type = InputType[InputType.TENSOR.name.upper()]
                model.build(weights_path=model_weights_path, input_type=input_type)

                sess.run(tf.global_variables_initializer())

                predictions = sess.run(model.predictions, feed_dict={model.input: final})

                print("\tSFW score:\t{}\n\tNSFW score:\t{}".format(*predictions[0]))
                pred = {"sfw_score": "{}".format(*predictions[0])}
                return flask.jsonify(pred)

if __name__ == "__main__":
    app.run(debug=True)
    
