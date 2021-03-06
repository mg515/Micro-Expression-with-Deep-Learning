import numpy as np
import sys
import math
import operator
import csv
import glob,os
import xlrd
import cv2
import pandas as pd

from sklearn.svm import SVC
from collections import Counter
from sklearn.metrics import confusion_matrix
import scipy.io as sio

from keras.models import Sequential, Model
from keras.layers.core import Flatten, Dense, Dropout
from keras.layers.convolutional import Conv2D, Conv3D, MaxPooling2D, ZeroPadding2D
from keras.layers.convolutional import Convolution3D, MaxPooling3D, ZeroPadding3D
from keras.layers import LSTM, GlobalAveragePooling2D, GRU, Bidirectional, UpSampling2D, BatchNormalization, concatenate, Input
from keras.optimizers import SGD
import keras.backend as K
from keras.callbacks import Callback
from keras.engine.topology import Layer

from labelling import collectinglabel
#from reordering import readinput
from evaluationmatrix import fpr

def VGG_16_4_channels(spatial_size, classes, channels, channel_first=True, weights_path=None):
	model = Sequential()

	if channel_first:
		model.add(ZeroPadding2D((1,1),input_shape=(channels, spatial_size, spatial_size)))
	else:
		model.add(ZeroPadding2D((1,1),input_shape=(spatial_size, spatial_size, channels)))

	model.add(Conv2D(64, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(64, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2)))

	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(128, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(128, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2)))

	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(256, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(256, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(256, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2)))

	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2)))

	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2))) # 33

	model.add(Flatten())
	model.add(Dense(4096, activation='relu')) # 34
	model.add(Dropout(0.5))
	model.add(Dense(4096, activation='relu')) # 35
	model.add(Dropout(0.5))
	model.add(Dense(2622, activation='softmax')) # Dropped


	if weights_path:
		model.load_weights(weights_path)
	model.pop()
	model.add(Dense(classes, activation='softmax')) # 36
	
	return model

def VGG_16(spatial_size, classes, channels, channel_first=False, weights_path=None):
	model = Sequential()
	if channel_first:
		model.add(ZeroPadding2D((1,1),input_shape=(channels, spatial_size, spatial_size)))
	else:
		model.add(ZeroPadding2D((1,1),input_shape=(spatial_size, spatial_size, channels)))


	model.add(Conv2D(64, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(64, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2)))

	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(128, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(128, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2)))

	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(256, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(256, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(256, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2)))

	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2)))

	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2))) # 33

	model.add(Flatten())
	model.add(Dense(4096, activation='relu', name = 'dense_prvi')) # 34
	model.add(Dropout(0.5))
	model.add(Dense(4096, activation='relu', name = 'dense_drugi')) # 35
	model.add(Dropout(0.5))
	model.add(Dense(2622, activation='softmax')) # Dropped


	if weights_path:
		model.load_weights(weights_path)
	model.pop()
	model.add(Dense(classes, activation='softmax')) # 36

	return model


def temporal_module(data_dim, timesteps_TIM, classes, lstm1_size, weights_path=None):
	model = Sequential()
	model.add(LSTM(lstm1_size, return_sequences=True, input_shape=(timesteps_TIM, data_dim)))
	model.add(LSTM(lstm1_size, return_sequences=False))
	model.add(Dense(128, activation='relu'))
	model.add(Dense(classes, activation='sigmoid'))

	if weights_path:
		model.load_weights(weights_path)

	print(model.summary())
	return model	

	


def convolutional_autoencoder(classes, spatial_size, channel_first=True, weights_path=None):
	model = Sequential()

	# encoder
	if channel_first:
		model.add(Conv2D(128, (3, 3), activation='relu', input_shape=(3, spatial_size, spatial_size), padding='same'))
	else:
		model.add(Conv2D(128, (3, 3), activation='relu', input_shape=(spatial_size, spatial_size, 3), padding='same'))

	model.add(MaxPooling2D( pool_size=(2, 2), strides=2, padding='same'))
	model.add(Conv2D(64, (3, 3), activation='relu', padding='same'))
	model.add(MaxPooling2D( pool_size=(2, 2), strides=2, padding='same'))
	model.add(Conv2D(64, (3, 3), activation='relu', padding='same'))
	model.add(MaxPooling2D( pool_size=(2, 2), strides=2, padding='same'))

	# decoder
	model.add(Conv2D(64, (3, 3), activation='relu', padding='same'))
	model.add(UpSampling2D(2))
	model.add(Conv2D(64, (3, 3), activation='relu', padding='same'))
	model.add(UpSampling2D(2))	
	model.add(Conv2D(128, (3, 3), activation='relu', padding='same'))
	model.add(UpSampling2D(2))
	model.add(Conv2D(3, (3, 3), activation='sigmoid', padding='same'))


	return model


def VGG_16_tim(spatial_size, classes, channels, channel_first=True, weights_path=None):
	model = Sequential()
	if channel_first:
		model.add(ZeroPadding2D((1,1),input_shape=(channels, spatial_size, spatial_size)))
	else:
		model.add(ZeroPadding2D((1,1),input_shape=(spatial_size, spatial_size, channels)))


	model.add(Conv2D(64, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(64, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2)))

	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(128, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(128, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2)))

	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(256, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(256, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(256, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2)))

	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2)))

	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(ZeroPadding2D((1,1)))
	model.add(Conv2D(512, (3, 3), activation='relu'))
	model.add(MaxPooling2D((2,2), strides=(2,2))) # 33

	model.add(Flatten())
	model.add(Dense(4096, activation='relu')) # 34
	model.add(Dropout(0.5))
	model.add(Dense(4096, activation='relu')) # 35
	model.add(Dropout(0.5))
	model.add(Dense(2622, activation='softmax')) # Dropped


	if weights_path:
		model.load_weights(weights_path)
	model.pop()
	model.add(Dense(classes, activation='softmax')) # 36
	
	return model


def c3d_channels(spatial_size, temporal_size, classes, channels, weights_path=None):
	model = Sequential()
	model.add(Convolution3D(filters=64,
							kernel_size=(5, 4, 4),
							strides=(1,2,2),
							padding="same",
							activation='relu',
							name='conv1',
							input_shape=(temporal_size, spatial_size, spatial_size, channels)))

	model.add(MaxPooling3D(pool_size=(2, 2, 2), strides=(2, 2, 2), padding="valid", name='pool1'))

	model.add(Convolution3D(filters=128,
							kernel_size=(5,4,4),
							strides=(1,2,2),
							padding="same",
							activation='relu',
							name='conv2'))

	model.add(MaxPooling3D(pool_size=(2, 2, 2), strides=(2, 2, 2), padding="valid", name='pool2'))

	model.add(Dense(1024, activation = 'relu'))
	model.add(Dropout(0.25))
	model.add(Flatten())

	if weights_path:
		model.load_weights(weights_path)
	model.add(Dense(classes, activation='softmax'))

	print(model.summary())
	return model



def c3d_2stream(spatial_size, temporal_size, classes, channels, weights_path=None):
	

	a = Input(shape=(temporal_size, spatial_size, spatial_size, 1))
	b = Input(shape=(temporal_size, spatial_size, spatial_size, 1))

	u = Conv3D(filters = 32,
				kernel_size = (4,3,3),
				strides = (2,2,2),
				padding = "same",
				activation = 'relu',
				name = 'conv1_u')(a)


	v = Conv3D(filters = 32,
				kernel_size = (4,3,3),
				strides = (2,2,2),
				padding = "same",
				activation = 'relu',
				name = 'conv1_v')(b)

	u = MaxPooling3D(pool_size = (1,2,2), strides = (1,2,2), padding = "same", name = 'pool1_u')(u)
	v = MaxPooling3D(pool_size = (1,2,2), strides = (1,2,2), padding = "same", name = 'pool1_v')(v)

	u = Conv3D(filters = 64,
			kernel_size = (4,3,3),
			strides = (2,2,2),
			padding = "same",
			activation = 'relu',
			name = 'conv2_u')(u)


	v = Conv3D(filters = 64,
			kernel_size = (4,3,3),
			strides = (2,2,2),
			padding = "same",
			activation = 'relu',
			name = 'conv2_v')(v)

	u = MaxPooling3D(pool_size = (1,2,2), strides = (1,2,2), padding = "same", name = 'pool2_u')(u)
	v = MaxPooling3D(pool_size = (1,2,2), strides = (1,2,2), padding = "same", name = 'pool2_v')(v)

	u = Flatten()(u)
	v = Flatten()(v)

	x = concatenate([u,v])

	x = Dense(1024, activation='relu', name = 'dense_1')(x)
	x = Dense(1024, activation='relu', name = 'dense_2')(x)
	x = Dropout(0.25)(x)

	x = Dense(classes, activation='softmax', name = 'dense_3')(x)

	model = Model(inputs = [a,b], outputs = x)

	if weights_path:
		model.load_weights(weights_path)

	print(model.summary())
	return model


def apex_cnn(spatial_size, temporal_size, classes, channels, weights_path=None, filters = 8):

	a = Input(shape=(1,spatial_size, spatial_size))
	b = Input(shape=(1,spatial_size, spatial_size))


	u = Conv2D(filters=filters,
				kernel_size=(4, 4),
				strides=(2,2),
				padding="same",
				activation='relu',
				name='conv1_u')(a)

	u = MaxPooling2D(pool_size=(2, 2), strides=(1, 1), padding="same", name='pool1_u')(u)

	v = Conv2D(filters=filters,
				kernel_size=(4, 4),
				strides=(2,2),
				padding="same",
				activation='relu',
				name='conv1_v')(b)

	v = MaxPooling2D(pool_size=(2, 2), strides=(1, 1), padding="same", name='pool1_v')(v)


	u = Conv2D(filters=filters*2,
							kernel_size=(4, 4),
							strides=(2,2),
							padding="same",
							activation='relu',
							name='conv2_u')(u)

	u = MaxPooling2D(pool_size=(2, 2), strides=(1, 1), padding="same", name='pool2_u')(u)

	v = Conv2D(filters=filters*2,
							kernel_size=(4, 4),
							strides=(2,2),
							padding="same",
							activation='relu',
							name='conv2_v')(v)

	v = MaxPooling2D(pool_size=(2, 2), strides=(1, 1), padding="same", name='pool2_v')(v)


	u = Conv2D(filters=filters*4,
							kernel_size=(4, 4),
							strides=(2,2),
							padding="same",
							activation='relu',
							name='conv3_u')(u)

	u = MaxPooling2D(pool_size=(2, 2), strides=(1, 1), padding="same", name='pool3_u')(u)

	v = Conv2D(filters=filters*4,
							kernel_size=(4, 4),
							strides=(2,2),
							padding="same",
							activation='relu',
							name='conv3_v')(v)

	v = MaxPooling2D(pool_size=(2, 2), strides=(1, 1), padding="same", name='pool3_v')(v)


	u = Flatten()(u)
	v = Flatten()(v)

	x = concatenate([u,v])


	x = Dense(1024, activation='relu', name = 'dense_1')(x)
	x = Dense(1024, activation='relu', name = 'dense_2')(x)
	x = Dropout(0.25)(x)

	x = Dense(classes, activation='softmax', name = 'dense_3')(x)

	model = Model(inputs = [a,b], outputs = x)

	print(model.summary())
	return model
