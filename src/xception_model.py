"""
Author: Abner Ayala-Acevedo

This script based on examples provided in the keras documentation and a blog.
"Building powerful image classification models using very little data"
from blog.keras.io.

Dataset: Subset of Kaggle Dataset
https://www.kaggle.com/c/dogs-vs-cats/data
- cat pictures index 0-999 in data/train/cats
- cat pictures index 1000-1400 in data/validation/cats
- dogs pictures index 0-999 in data/train/dogs
- dog pictures index 1000-1400 in data/validation/dogs

Example: Dogs vs Cats (Directory Structure)
data/
    train/
        dogs/
            dog001.jpg
            dog002.jpg
            ...
        cats/
            cat001.jpg
            cat002.jpg
            ...
    validation/
        dogs/
            dog001.jpg
            dog002.jpg
            ...
        cats/
            cat001.jpg
            cat002.jpg
            ...

Example has 1000 training examples for each class, and 400 validation examples for each class.
The data folder already contains the dogs vs cat data you simply need to run script. For the dogs_cats classification
you can find a model already trained in the model folder. Feel free to create your own data.
"""

import sys
import os
from keras.layers import *
from keras.optimizers import *
from keras.applications import *
from keras.models import Model
from keras.preprocessing.image import ImageDataGenerator
from keras.callbacks import ModelCheckpoint, EarlyStopping
from keras import backend as k

# fix seed for reproducible results (only works on CPU, not GPU)
seed = 9
np.random.seed(seed=seed)
tf.set_random_seed(seed=seed)

# hyper parameters for model
nb_classes = 149  # number of classes
based_model_last_block_layer_number = 126  # value is based on based model selected.
img_width, img_height = 299, 299  # change based on the shape/structure of your images
batch_size = 32  # try 4, 8, 16, 32, 64, 128, 256 dependent on CPU/GPU memory capacity (powers of 2 values).
nb_epoch = 50  # number of iteration the algorithm gets trained.
learn_rate = 1e-4  # sgd learning rate
momentum = .9  # sgd momentum to avoid local minimum
transformation_ratio = .05  # how aggressive will be the data augmentation/transformation


def train(train_data_dir, validation_data_dir, test_data_dir, model_path):
    # Pre-Trained CNN Model using imagenet dataset for pre-trained weights
    base_model = Xception(input_shape=(img_width, img_height, 3), weights='imagenet', include_top=False)

    # Top Model Block
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    predictions = Dense(nb_classes, activation='softmax')(x)

    # add your top layer block to your base model
    model = Model(base_model.input, predictions)
    print(model.summary())

    # # let's visualize layer names and layer indices to see how many layers/blocks to re-train
    # # uncomment when choosing based_model_last_block_layer
    # for i, layer in enumerate(model.layers):
    #     print(i, layer.name)

    # first: train only the top layers (which were randomly initialized)
    # i.e. freeze all layers of the based model that is already pre-trained.
    for layer in base_model.layers:
        layer.trainable = False

    # Read Data and Augment it: Make sure to select augmentations that are appropriate to your images.
    # To save augmentations un-comment save lines and add to your flow parameters.
    train_datagen = ImageDataGenerator(rescale=1. / 255,
                                       rotation_range=transformation_ratio,
                                       shear_range=transformation_ratio,
                                       zoom_range=transformation_ratio,
                                       cval=transformation_ratio,
                                       horizontal_flip=True,
                                       vertical_flip=True)

    validation_datagen = ImageDataGenerator(rescale=1. / 255)

    os.makedirs(os.path.join(os.path.abspath(train_data_dir), '../preview'), exist_ok=True)
    train_generator = train_datagen.flow_from_directory(train_data_dir,
                                                        target_size=(img_width, img_height),
                                                        batch_size=batch_size,
                                                        class_mode='categorical')
    # save_to_dir=os.path.join(os.path.abspath(train_data_dir), '../preview')
    # save_prefix='aug',
    # save_format='jpeg')
    # use the above 3 commented lines if you want to save and look at how the data augmentations look like

    validation_generator = validation_datagen.flow_from_directory(validation_data_dir,
                                                                  target_size=(img_width, img_height),
                                                                  batch_size=batch_size,
                                                                  class_mode='categorical')

    test_generator = validation_datagen.flow_from_directory(test_data_dir,
                                                                  target_size=(img_width, img_height),
                                                                  batch_size=batch_size,
                                                                  class_mode='categorical')
    model.compile(optimizer='nadam',
                  loss='categorical_crossentropy',  # categorical_crossentropy if multi-class classifier
                  metrics=['accuracy'])

    # save weights of best training epoch: monitor either val_loss or val_acc

    top_weights_path = os.path.join(os.path.abspath(model_path), 'top_model_weights.h5')
    callbacks_list = [
        ModelCheckpoint(top_weights_path, monitor='val_acc', verbose=1, save_best_only=True),
        EarlyStopping(monitor='val_acc', patience=5, verbose=0)
    ]
    n_train = sum(len(files) for _, _, files in os.walk("../data/train"))  # : number of training samples

    n_test = sum(len(files) for _, _, files in os.walk("../data/val"))  # : number of validation samples
    # Train Simple CNN
    model.fit_generator(train_generator,
                        steps_per_epoch=n_train,
                        epochs=nb_epoch / 5,
                        validation_data=validation_generator,
                        validation_steps=n_test,
                        callbacks=callbacks_list)

    # verbose
    print("\nStarting to Fine Tune Model\n")

    # add the best weights from the train top model
    # at this point we have the pre-train weights of the base model and the trained weight of the new/added top model
    # we re-load model weights to ensure the best epoch is selected and not the last one.
    model.load_weights(top_weights_path)

    # based_model_last_block_layer_number points to the layer in your model you want to train.
    # For example if you want to train the last block of a 19 layer VGG16 model this should be 15
    # If you want to train the last Two blocks of an Inception model it should be 172
    # layers before this number will used the pre-trained weights, layers above and including this number
    # will be re-trained based on the new data.
    for layer in model.layers[:based_model_last_block_layer_number]:
        layer.trainable = False
    for layer in model.layers[based_model_last_block_layer_number:]:
        layer.trainable = True

    # compile the model with a SGD/momentum optimizer
    # and a very slow learning rate.
    model.compile(optimizer='nadam',
                  loss='categorical_crossentropy',
                  metrics=['accuracy'])

    # save weights of best training epoch: monitor either val_loss or val_acc
    final_weights_path = os.path.join(os.path.abspath(model_path), 'model_weights.h5')
    callbacks_list = [
        ModelCheckpoint(final_weights_path, monitor='val_acc', verbose=1, save_best_only=True),
        EarlyStopping(monitor='val_loss', patience=5, verbose=0)
    ]

    # fine-tune the model
    model.fit_generator(train_generator,
                        steps_per_epoch=n_train,
                        epochs=nb_epoch,
                        validation_data=validation_generator,
                        validation_steps=n_test,
                        callbacks=callbacks_list)

    # save model
    model_json = model.to_json()
    with open(os.path.join(os.path.abspath(model_path), 'model.json'), 'w') as json_file:
        json_file.write(model_json)


if __name__ == '__main__':
    if not len(sys.argv) == 3:
        print('Arguments must match:\npython code/train.py <data_dir/> <model_dir/>')
        print('Example: python code/train.py data/dogs_cats/ model/dog_cats/')
        sys.exit(2)
    else:
        data_dir = os.path.abspath(sys.argv[1])
        train_dir = os.path.join(os.path.abspath(data_dir), 'train')  # Inside, each class should have it's own folder
        test_dir = os.path.join(os.path.abspath(data_dir), "test")
        validation_dir = os.path.join(os.path.abspath(data_dir), 'val')  # each class should have it's own folder
        model_dir = os.path.abspath(sys.argv[2])

        os.makedirs(os.path.join(os.path.abspath(data_dir), 'preview'), exist_ok=True)
        os.makedirs(model_dir, exist_ok=True)

    train(train_dir, validation_dir, train_dir, model_dir)  # train model

    # release memory
    k.clear_session()















"""import keras
import os
import numpy as np
import pandas as pd
from keras.applications import MobileNet, Xception
from keras.applications.xception import preprocess_input
from keras.layers import Dense, GlobalAveragePooling2D
from keras.models import Model, load_model
from keras.preprocessing.image import ImageDataGenerator

size = (299, 299)
batch = 32

def create_data_generators(size=(299, 299), batch=32, preprocessing_func=preprocess_input):
    train_datagen = ImageDataGenerator(
     preprocessing_function=preprocess_input,
     rotation_range=6,
     width_shift_range=0.1,
     height_shift_range=0.1,
     brightness_range=[0.15, 0.85],
     shear_range=0.1,
     zoom_range=0.1,
     horizontal_flip=True)


    test_datagen = ImageDataGenerator(preprocessing_function=preprocess_input)


    train_generator = train_datagen.flow_from_directory(
        '../data/train',
        target_size=size,
        batch_size=batch,
        class_mode='categorical',
        shuffle=True)
        
    holdout_generator = test_datagen.flow_from_directory(
        '../data/test',
        target_size=size,
        batch_size=batch,
        class_mode='categorical',
        shuffle=False)

    validate_generator = test_datagen.flow_from_directory(
        '../data/val',
        target_size=size,
        batch_size=batch,
        class_mode='categorical',
        shuffle=False)

    return train_generator, validate_generator, holdout_generator


original = load_img(filename, target_size = (299,299))
numpy_image = preprocess_input( img_to_array(original))
image_batch = np.expand_dims(numpy_image, axis =0)


category_df = pd.DataFrame([(len(files), os.path.basename(dirname)) for dirname, _, files in os.walk("../data/train")]).drop(0)
category_df.columns = ["n_images", "class"]
category_df = category_df.sort_values("class")
weights = category_df["n_images"]/category_df["n_images"].sum()
training_weight_dict = dict(zip(range(weights.shape[0]), weights.values))




n_train = sum(len(files) for _, _, files in os.walk("../data/train"))  # : number of training samples

n_test = sum(len(files) for _, _, files in os.walk("../data/val"))  # : number of validation samples

n_holdout = sum(len(files) for _, _, files in os.walk("../data/test"))

train_generator, test_generator, holdout_generator = create_data_generators(size, batch, preprocess_input)
model = Xception(weights='imagenet', include_top=False, input_shape=size + (3,))
model.compile(optimizer="adam", loss='categorical_crossentropy', metrics=["accuracy"])


tensorboard = keras.callbacks.TensorBoard(log_dir="../data", histogram_freq=0, batch_size=batch, write_graph=True, embeddings_freq=0)

mc = keras.callbacks.ModelCheckpoint("../data", monitor='val_loss', verbose=0, save_best_only=True, save_weights_only=False, mode='auto', period=1)
callbacks = [mc, tensorboard]



model.fit_generator(train_generator,
                    class_weight=training_weight_dict,
                    steps_per_epoch=n_train/batch,
                    epochs=3,
                    validation_data=test_generator,
                    validation_steps=n_test/batch,
                    use_multiprocessing=True,
                    callbacks=callbacks)

metrics = model.evaluate_generator(holdout_generator,
                                           steps=n_holdout/batch,
                                           use_multiprocessing=True,
                                           verbose=1)
print(f"holdout loss: {metrics[0]} accuracy: {metrics[1]}")"""