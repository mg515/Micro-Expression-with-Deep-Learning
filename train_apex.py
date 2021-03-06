import numpy as np
import sys
import math
import operator
import csv
import glob,os
import xlrd
import cv2
import pandas as pd
import matplotlib.pyplot as plt
import gc

from sklearn.svm import SVC
from collections import Counter
from sklearn.metrics import confusion_matrix
import scipy.io as sio
import pydot, graphviz
from PIL import Image


from keras.models import Sequential, Model
from keras.utils import np_utils, plot_model
from keras.models import model_from_json
from keras.layers import Dense, Dropout, Flatten, Activation, GlobalAveragePooling2D
from keras.layers import Conv2D, MaxPooling2D
from keras.preprocessing.sequence import pad_sequences
from keras import optimizers
from keras.applications.vgg16 import VGG16 as keras_vgg16
from keras.preprocessing.image import ImageDataGenerator, array_to_img
from keras.callbacks import EarlyStopping
from keras import metrics
from keras import backend as K

from labelling import collectinglabel
#from reordering import readinput
from evaluationmatrix import fpr, weighted_average_recall, unweighted_average_recall
from utilities import *
#from samm_utilitis import get_subfolders_num_crossdb, Read_Input_Images_SAMM_CASME, loading_samm_labels

from list_databases import load_db, restructure_data_c3d, restructure_data_apex
from models import VGG_16, temporal_module, VGG_16_4_channels, convolutional_autoencoder

from data_preprocess import optical_flow_2d

import ipdb

#python main.py --dB 'CASME2_Cropped' --batch_size=5 --spatial_epochs=30 --train_id='casme2_apex_1' --spatial_size=224 --train='./train_apex.py'
def train_apex(batch_size, spatial_epochs, train_id, list_dB, spatial_size, objective_flag, tensorboard):
	############## Path Preparation ######################
	root_db_path = "/media/ostalo/MihaGarafolj/ME_data/"
	#root_db_path = '/home/miha/Documents/ME_data/'
	tensorboard_path = root_db_path + "tensorboard/"
	if os.path.isdir(root_db_path + 'Weights/'+ str(train_id) ) == False:
		os.mkdir(root_db_path + 'Weights/'+ str(train_id) )

	######################################################

	############## Variables ###################
	dB = list_dB[0]
	r, w, subjects, samples, n_exp, VidPerSubject, vidList, timesteps_TIM, data_dim, channel, table, listOfIgnoredSamples, db_home, db_images, cross_db_flag = load_db(root_db_path, list_dB, spatial_size, objective_flag)


	# avoid confusion
	if cross_db_flag == 1:
		list_samples = listOfIgnoredSamples

	# total confusion matrix to be used in the computation of f1 score
	tot_mat = np.zeros((n_exp, n_exp))

	history = LossHistory()
	stopping = EarlyStopping(monitor='loss', min_delta = 0, mode = 'min', patience = 5)

	############################################

	############## Flags ####################
	tensorboard_flag = tensorboard
	resizedFlag = 1
	#svm_flag = 0
	#finetuning_flag = 0
	cam_visualizer_flag = 0
	#channel_flag = 0			

	#########################################

	############ Reading Images and Labels ################
	if cross_db_flag == 1:
		SubperdB = Read_Input_Images_SAMM_CASME(db_images, list_samples, listOfIgnoredSamples, dB, resizedFlag, table, db_home, spatial_size, channel)
	else:
		SubperdB = Read_Input_Images_Apex(db_images, listOfIgnoredSamples, dB, resizedFlag, table, db_home, spatial_size, channel, objective_flag)
        
	labelperSub = label_matching(db_home, dB, subjects, VidPerSubject)
	print(labelperSub)
	print("Loaded Images into the tray.")
	print("Loaded Labels into the tray.")
	
	#######################################################
	# PREPROCESSING STEPS
	# optical flow

	#import ipdb
	#ipdb.set_trace()
	#SubperdB = optical_flow_2d(SubperdB, samples, r, w, timesteps_TIM)

	########### Model Configurations #######################
	#K.set_image_dim_ordering('th')

	# config = tf.ConfigProto()
	# config.gpu_options.allow_growth = True
	# config.gpu_options.per_process_gpu_memory_fraction = 0.8
	# K.tensorflow_backend.set_session(tf.Session(config=config))


	########################################################

	print("Beginning training process.")
	########### Training Process ############
	subjects_todo = read_subjects_todo(db_home, dB, train_id, subjects)

	for sub in subjects_todo:
		print("**** starting subject " + str(sub) + " ****")
#		gpu_observer()
		#spatial_weights_name = root_db_path + 'Weights/'+ str(train_id) + '/c3d_'+ str(train_id) + '_' + str(dB) + '_'

		adam = optimizers.Adam(lr=0.00001, decay=0.000001)

		############### Reinitialization & weights reset of models ########################

		apex_model = apex_cnn(spatial_size=spatial_size, temporal_size=timesteps_TIM, classes=n_exp, channels=2, filters=16)
		apex_model.compile(loss='categorical_crossentropy', optimizer=adam, metrics=[metrics.categorical_accuracy])

		#svm_classifier = SVC(kernel='linear', C=1)
		####################################################################################
		
		
		############ for tensorboard ###############
		if tensorboard_flag == 1:
			cat_path2 = tensorboard_path + str(train_id) +  str(sub) + "apex/"
			if os.path.exists(cat_path2):
				os.rmdir(cat_path2)
			os.mkdir(cat_path2)
			tbCallBack2 = keras.callbacks.TensorBoard(log_dir=cat_path2, write_graph=True)
		#############################################

		Train_X, Train_Y, Train_Y_gt, Test_X, Test_Y, Test_Y_gt = restructure_data_apex(sub, SubperdB, labelperSub, subjects, n_exp, r, w, timesteps_TIM, channel)
		#Train_X, Train_Y, Train_Y_gt = upsample_training_set(Train_X, Train_Y, Train_Y_gt)
		#Train_X, Test_X = optical_flow_2d_old(Train_X, Test_X, r, w, timesteps_TIM)


		############### check gpu resources ####################
#		gpu_observer()
		########################################################

		print("Beginning training & testing.")
		##################### Training & Testing #########################

		print("Beginning c3d training.")

		# Spatial Training
		input_u = Train_X[:,0,:,:].reshape(Train_X.shape[0],1,r,w)
		input_v = Train_X[:,1,:,:].reshape(Train_X.shape[0],1,r,w)
		if tensorboard_flag == 1:
			apex_model.fit([input_u, input_v], Train_Y, batch_size=batch_size, epochs=spatial_epochs, shuffle=True, callbacks=[history,stopping,tbCallBack2])
		else:
			apex_model.fit([input_u, input_v], Train_Y, batch_size=batch_size, epochs=spatial_epochs, shuffle=True, callbacks=[history,stopping])


		print(".record f1 and loss")
		# record f1 and loss
		record_loss_accuracy(db_home, train_id, dB, history)

		print("Beginning testing.")
		print(".predicting with c3d_model")
		# Testing
		input_u = Test_X[:,0,:,:].reshape(Test_X.shape[0],1,r,w)
		input_v = Test_X[:,1,:,:].reshape(Test_X.shape[0],1,r,w)
		predict_values = apex_model.predict([input_u, input_v], batch_size = batch_size)
		predict = np.array([np.argmax(x) for x in predict_values])
		##############################################################

		#################### Confusion Matrix Construction #############
		print (predict)
		print (Test_Y_gt.astype(int))

		print(".writing predicts to file")
		file = open(db_home+'Classification/'+ 'Result/'+'/predicts_' + str(train_id) +  '.txt', 'a')
		for i in range(len(vidList[sub])):
			file.write("sub_" + str(sub) + "," + str(vidList[sub][i]) + "," + str(predict.astype(list)[i]) + "," + str(Test_Y_gt.astype(int).astype(list)[i]) + "\n")
		file.close()

		file = open(db_home+'Classification/'+ 'Result/'+'/predictedvalues_' + str(train_id) +  '.txt', 'a')
		for i in range(len(vidList[sub])):
			file.write("sub_" + str(sub) + "," + str(vidList[sub][i]) + "," + ','.join(str(e) for e in predict_values[i]) + "," + str(Test_Y_gt.astype(int).astype(list)[i]) + "\n")
		file.close()

		ct = confusion_matrix(Test_Y_gt,predict)
		# check the order of the CT
		order = np.unique(np.concatenate((predict,Test_Y_gt)))
		
		# create an array to hold the CT for each CV
		mat = np.zeros((n_exp,n_exp))
		# put the order accordingly, in order to form the overall ConfusionMat
		for m in range(len(order)):
			for n in range(len(order)):
				mat[int(order[m]),int(order[n])]=ct[m,n]
			   
		tot_mat = mat + tot_mat
		################################################################
		
		#################### cumulative f1 plotting ######################
		microAcc = np.trace(tot_mat) / np.sum(tot_mat)
		[f1,precision,recall] = fpr(tot_mat,n_exp)

		file = open(db_home+'Classification/'+ 'Result/'+'/f1_' + str(train_id) +  '.txt', 'a')
		file.write(str(f1) + "\n")
		file.close()
		##################################################################

		################# write each CT of each CV into .txt file #####################
		record_scores(db_home, dB, ct, sub, order, tot_mat, n_exp, subjects)
		war = weighted_average_recall(tot_mat, n_exp, samples)
		uar = unweighted_average_recall(tot_mat, n_exp)
		print("war: " + str(war))
		print("uar: " + str(uar))
		###############################################################################

		################## free memory ####################

		del apex_model
		del Train_X, Test_X, Train_Y, Test_Y, input_u, input_v
		K.get_session().close()
		cfg = K.tf.ConfigProto()
		cfg.gpu_options.allow_growth = True
		K.set_session(K.tf.Session(config=cfg))
		
		gc.collect()
		###################################################
