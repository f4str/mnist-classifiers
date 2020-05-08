import numpy as np
import tensorflow as tf
import data_loader
import layers

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)


class Convolutional:
	def __init__(self, learning_rate=0.001, batch_size=128, early_stopping=True, patience=4):
		self.sess = tf.Session()
		
		self.learning_rate = learning_rate
		self.batch_size = batch_size
		self.early_stopping = early_stopping
		self.patience = patience
		
		self.build()
	
	def build(self):
		# inputs
		self.X = tf.placeholder(tf.float32, [None, 28, 28])
		self.y = tf.placeholder(tf.int32, [None])
		one_hot_y = tf.one_hot(self.y, 10)
		
		# create batch iterator
		dataset = tf.data.Dataset.from_tensor_slices((self.X, self.y))
		dataset = dataset.shuffle(self.batch_size, reshuffle_each_iteration=True).batch(self.batch_size)
		self.iterator = dataset.make_initializable_iterator()
		self.X_batch, self.y_batch = self.iterator.get_next()
		
		# reshape: 28x28 -> 28x28@1
		reshaped = tf.reshape(self.X, shape=[-1, 28, 28, 1])
		# convolution: 28x28@1 -> 28x28@16 + relu
		conv = layers.conv2d(reshaped, filters=16, padding='SAME')
		conv = tf.nn.relu(conv)
		# max pooling: 28x28@16 -> 14x14@16
		pool = layers.maxpool2d(conv, padding='SAME')
		# flatten: 14x14@16 -> 3136
		flat = layers.flatten(pool)
		# linear: 3136 -> 512 + relu
		linear = layers.linear(flat, num_outputs=512)
		linear = tf.nn.relu(linear)
		# linear: 512 -> 10
		logits = layers.linear(linear, num_outputs=10)
		
		cross_entropy = tf.nn.softmax_cross_entropy_with_logits_v2(logits=logits, labels=one_hot_y)
		self.loss = tf.reduce_mean(cross_entropy)
		optimizer = tf.train.AdamOptimizer(learning_rate=self.learning_rate)
		self.train_op = optimizer.minimize(self.loss)
		
		correct_prediction = tf.equal(tf.argmax(logits, axis=1), tf.argmax(one_hot_y, axis=1))
		self.accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
		self.prediction = tf.argmax(logits)
	
	def fit(self, X, y, epochs=100, validation_split=0.2, verbose=True):
		# split into train and validation sets
		X = np.array(X)
		y = np.array(y)
		indices = np.random.permutation(X.shape[0])
		split = int(validation_split * len(X))
		
		X_train = X[indices[split:]] 
		y_train = y[indices[split:]]
		X_valid = X[indices[:split]]
		y_valid = y[indices[:split]]
		
		total_train_loss = []
		total_train_acc = []
		total_valid_loss = []
		total_valid_acc = []
		best_acc = 0
		no_acc_change = 0
		
		self.sess.run(tf.global_variables_initializer())
		
		for e in range(epochs):
			# initialize batch iterator with train data
			self.sess.run(
				self.iterator.initializer, 
				feed_dict={self.X: X_train, self.y: y_train}
			)
			
			# train on training data
			total_loss = 0
			total_acc = 0
			try:
				batch = 0
				while True:
					X_batch, y_batch = self.sess.run([self.X_batch, self.y_batch])
					_, loss, acc = self.sess.run(
						[self.train_op, self.loss, self.accuracy], 
						feed_dict={self.X: X_batch, self.y: y_batch}
					)
					total_loss += loss * len(y_batch)
					total_acc += acc * len(y_batch)
					
					if verbose:
						batch += len(y_batch)
						print(f'epoch {e + 1}: {batch} / {len(y_train)}', end='\r')
			except tf.errors.OutOfRangeError:
				pass
			
			train_loss = total_loss / len(y_train)
			train_acc = total_acc / len(y_train)
			
			# test on validation data
			valid_loss, valid_acc = self.sess.run(
				[self.loss, self.accuracy], 
				feed_dict={self.X: X_valid, self.y: y_valid}
			)
			
			total_train_loss.append(train_loss)
			total_train_acc.append(train_acc)
			total_valid_loss.append(valid_loss)
			total_valid_acc.append(valid_acc)
			
			if verbose:
				print(f'epoch {e + 1}:',
					f'train loss = {train_loss:.4f},',
					f'train acc = {train_acc:.4f},',
					f'valid loss = {valid_loss:.4f},',
					f'valid acc = {valid_acc:.4f}'
				)
			
			# early stopping
			if self.early_stopping:
				if valid_acc > best_acc:
					best_acc = valid_acc
					no_acc_change = 0
				else:
					no_acc_change += 1
				
				if no_acc_change >= self.patience:
					if verbose:
						print('early stopping')
					break
		
		return total_train_loss, total_train_acc, total_valid_loss, total_valid_acc
	
	def evaluate(self, X, y):
		loss, acc = self.sess.run([self.loss, self.accuracy], feed_dict={self.X: X, self.y: y})
		return loss, acc
	
	def predict(self, X):
		y_pred = self.sess.run(self.prediction, feed_dict={self.X, X})
		return y_pred


if __name__ == '__main__':
	(X_train, y_train), (X_test, y_test) = data_loader.load_data(normalize=False)
	
	model = Convolutional()
	model.fit(X_train, y_train, epochs=10)
	loss, acc = model.evaluate(X_test, y_test)
	print(f'test loss: {loss:.4f}, test acc: {acc:.4f}')