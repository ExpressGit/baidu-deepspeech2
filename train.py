from model import Model, ModelModes
from config import hparams
import utils

import os
import time
import tensorflow as tf
import numpy as np

if __name__ == '__main__':

    train_graph = tf.Graph()
    eval_graph = tf.Graph()
    infer_graph = tf.Graph()

    print('Loading data...')

    output_mapping = utils.load_output_mapping('data/output_space.txt')
    hparams.n_classes = len(output_mapping) + 1  # not entirely sure we +1 here

    x_train, y_train, x_test, y_test = utils.load_data('data', max_data=hparams.max_data)

    hparams.input_max_len = max([max([len(x) for x in x_train]), max([len(x) for x in x_test])])

    x_train = utils.pad_sequences(x_train, hparams.input_max_len)
    x_test = utils.pad_sequences(x_test, hparams.input_max_len)

    print('Initializing model...')

    with train_graph.as_default():

        train_model = Model(hparams, ModelModes.TRAIN)
        variables_initializer = tf.global_variables_initializer()

    with eval_graph.as_default():

        eval_model = Model(hparams, ModelModes.EVAL)

    with infer_graph.as_default():

        infer_model = Model(hparams, ModelModes.INFER)

    train_sess = tf.Session(graph=train_graph)
    eval_sess = tf.Session(graph=eval_graph)
    infer_sess = tf.Session(graph=infer_graph)

    train_sess.run(variables_initializer)

    epoch = hparams.n_epochs
    batch_size = hparams.batch_size
    steps_per_checkpoint = hparams.steps_per_checkpoint
    checkpoints_path = hparams.checkpoints_path
    global_step = 0
    start_time = time.time()

    if not os.path.exists(checkpoints_path):
        os.makedirs(checkpoints_path)

    checkpoints_path = os.path.join(checkpoints_path, 'checkpoint')

    print('Training...')

    while epoch:

        current_epoch = hparams.n_epochs - epoch

        for i in range(int(len(x_train)/batch_size)):

            batch_train_x = np.asarray(x_train[i*batch_size:(i+1)*batch_size], dtype=np.float32)
            batch_train_y = utils.sparse_tuple_from(np.asarray(y_train[i * batch_size:(i + 1) * batch_size]))

            cost, _ = train_model.train(batch_train_x, batch_train_y, train_sess)

            global_step += batch_size

            print(f'epoch: {current_epoch}, global_step: {global_step}, cost: {cost}, time: {time.time() - start_time}')

            if global_step % steps_per_checkpoint == 0:

                print(f'checkpointing... (global step = {global_step})')

                checkpoint_path = train_model.saver.save(train_sess, checkpoints_path, global_step=global_step)
                eval_model.saver.restore(eval_sess, checkpoint_path)
                infer_model.saver.restore(infer_sess, checkpoint_path)

                # wer = eval_model.eval(batch_train_x, batch_train_y, eval_sess)
                #
                # print(f'Eval --- WER: {wer}')

                decoded_ids = infer_model.infer(batch_train_x[0], infer_sess)[0][0].values

                original_text = utils.ids_to_text(y_train[i*batch_size], output_mapping)
                decoded_text = utils.ids_to_text(decoded_ids, output_mapping)

                print(f'GROUND TRUTH: {original_text}')
                print(f'PREDICTION: {decoded_text}')

        if epoch > 0: epoch -= 1