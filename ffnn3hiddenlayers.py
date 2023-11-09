import numpy as np
import torch
import torch.nn as nn
from torch.nn import init
import torch.optim as optim
import math
import random
import os
import time
from tqdm import tqdm
import json
from argparse import ArgumentParser
from nltk.corpus import stopwords
import matplotlib.pyplot as plt
from numpy import arange

unk = '<UNK>'
# Consult the PyTorch documentation for information on the functions used below:
# https://pytorch.org/docs/stable/torch.html
class FFNN(nn.Module):
    def __init__(self, input_dim, h):
        super(FFNN, self).__init__()
        self.h = h
        self.W1 = nn.Linear(input_dim, h)
        self.activation = nn.ReLU()# The rectified linear unit; one valid choice of activation function
        self.W11 = nn.Linear(h, 32)
        self.W111 = nn.Linear(32, 16)
        self.output_dim = 5
        self.W2 = nn.Linear(16, self.output_dim)
        self.softmax = nn.LogSoftmax(dim=0) # The softmax function that converts vectors into probability distributions; computes log probabilities for computational benefits
        self.loss = nn.NLLLoss() # The cross-entropy/negative log likelihood loss taught in class

    def compute_Loss(self, predicted_vector, gold_label):
        return self.loss(predicted_vector, gold_label)

    def forward(self, input_vector):
        # obtain first hidden layer representation
        hidden_representation = self.W1(input_vector)
        activated_hidden_representation = self.activation(hidden_representation)
        w11op = self.w11(activated_hidden_representation)
        actw11op = self.activation(w11op)
        w111op = self.w111(actw11op)
        actw111op = self.activation(w111op)
        # obtain output layer representation
        real_outputs = self.W2(actw111op)
        # obtain probability dist.
        predicted_vector = self.softmax(real_outputs)
        return predicted_vector


# Returns:
# vocab = A set of strings corresponding to the vocabulary
def make_vocab(data):
    vocab = set()
    for document, _ in data:
        for word in document:
            vocab.add(word)
    return vocab


# Returns:
# vocab = A set of strings corresponding to the vocabulary including <UNK>
# word2index = A dictionary mapping word/token to its index (a number in 0, ..., V - 1)
# index2word = A dictionary inverting the mapping of word2index
def make_indices(vocab):
    vocab_list = sorted(vocab)
    vocab_list.append(unk)
    word2index = {}
    index2word = {}
    for index, word in enumerate(vocab_list):
        word2index[word] = index
        index2word[index] = word
    vocab.add(unk)
    return vocab, word2index, index2word


# Returns:
# vectorized_data = A list of pairs (vector representation of input, y)
def convert_to_vector_representation(data, word2index):
    vectorized_data = []
    for document, y in data:
        vector = torch.zeros(len(word2index))
        for word in document:
            index = word2index.get(word, word2index[unk])
            vector[index] += 1
        vectorized_data.append((vector, y))
    return vectorized_data



def load_data(train_data, val_data):
    with open(train_data) as training_f:
        training = json.load(training_f)
    with open(val_data) as valid_f:
        validation = json.load(valid_f)

    tra = []
    val = []
    for elt in training:
        tra.append((elt["text"].lower().split(),int(elt["stars"]-1)))
    for elt in validation:
        val.append((elt["text"].lower().split(),int(elt["stars"]-1)))
    # print(tra[-1])
    english_stopwords = stopwords.words("english")
    tra = [([word for word in review[0] if word not in english_stopwords], review[1]) for review in tra]
    val = [([word for word in review[0] if word not in english_stopwords], review[1]) for review in val]
    # print(tra[-1])
    return tra, val


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-hd", "--hidden_dim", type=int, required = True, help = "hidden_dim")
    parser.add_argument("-e", "--epochs", type=int, required = True, help = "num of epochs to train")
    parser.add_argument("--train_data", required = True, help = "path to training data")
    parser.add_argument("--val_data", required = True, help = "path to validation data")
    parser.add_argument("--test_data", default = "to fill", help = "path to test data")
    parser.add_argument('--do_train', action='store_true')
    args = parser.parse_args()

    # fix random seeds
    random.seed(42)
    torch.manual_seed(42)

    # load data
    print("========== Loading data ==========")
    train_data1, valid_data1 = load_data(args.train_data, args.val_data) # X_data is a list of pairs (document, y); y in {0,1,2,3,4}
    vocab = make_vocab(train_data1)
    vocab, word2index, index2word = make_indices(vocab)

    print("========== Vectorizing data ==========")
    train_data = convert_to_vector_representation(train_data1, word2index)
    valid_data = convert_to_vector_representation(valid_data1, word2index)


    errors = []
    model = FFNN(input_dim = len(vocab), h = args.hidden_dim)
    optimizer = optim.SGD(model.parameters(),lr=0.0125, momentum=0.8)
    print("========== Training for {} epochs ==========".format(args.epochs))
    training_acc = []
    training_loss = []
    validation_acc = []
    validation_loss = []
    for epoch in range(args.epochs):
        model.train()
        optimizer.zero_grad()
        loss = None
        correct = 0
        total = 0
        start_time = time.time()
        print("Training started for epoch {}".format(epoch + 1))
        random.shuffle(train_data) # Good practice to shuffle order of training data
        minibatch_size = 16
        N = len(train_data)
        total_loss = 0

        for minibatch_index in tqdm(range(N // minibatch_size)):
            optimizer.zero_grad()
            loss = None
            for example_index in range(minibatch_size):
                input_vector, gold_label = train_data[minibatch_index * minibatch_size + example_index]
                predicted_vector = model(input_vector)
                # print(predicted_vector.view())
                # print(predicted_vector)
                predicted_label = torch.argmax(predicted_vector)
                # print(gold_label, predicted_label)
                correct += int(predicted_label == gold_label)
                total += 1
                example_loss = model.compute_Loss(predicted_vector.view(1,-1), torch.tensor([gold_label]))
                if loss is None:
                    loss = example_loss
                else:
                    loss += example_loss
            total_loss += loss.item()
            loss = loss / minibatch_size
            loss.backward()
            optimizer.step()
            # break
        print(type(loss))
        print("Training completed for epoch {}".format(epoch + 1))
        print("Training accuracy for epoch {}: {}".format(epoch + 1, correct / total))
        training_acc.append(correct/N)
        training_loss.append(total_loss / N)
        print("Training time for this epoch: {}".format(time.time() - start_time))


        loss = None
        correct = 0
        total = 0
        start_time = time.time()
        print("Validation started for epoch {}".format(epoch + 1))
        minibatch_size = 16
        N = len(valid_data)
        total_valid_loss = 0
        for minibatch_index in tqdm(range(N // minibatch_size)):
            optimizer.zero_grad()
            loss = None
            for example_index in range(minibatch_size):
                input_vector, gold_label = valid_data[minibatch_index * minibatch_size + example_index]
                predicted_vector = model(input_vector)
                # print(predicted_vector)
                predicted_label = torch.argmax(predicted_vector)
                # print(gold_label, predicted_label)
                correct += int(predicted_label == gold_label)
                if epoch == args.epochs - 1 and predicted_label != gold_label:
                    errors.append((minibatch_index * minibatch_size + example_index, predicted_label))
                total += 1
                example_loss = model.compute_Loss(predicted_vector.view(1,-1), torch.tensor([gold_label]))
                if loss is None:
                    loss = example_loss
                else:
                    loss += example_loss
            # break
            total_valid_loss += loss.item()
            loss = loss / minibatch_size

        validation_loss.append(total_valid_loss/total)
        print("Validation completed for epoch {}".format(epoch + 1))
        print("Validation accuracy for epoch {}: {}".format(epoch + 1, correct / total))
        validation_acc.append(correct / total)
        print("Validation time for this epoch: {}".format(time.time() - start_time))

    # write out to results/test.out

    x_range = range(1, args.epochs + 1)

    plt.plot(x_range, validation_acc, label='Validation Accuracy')
    plt.plot(x_range, training_loss, label='Training Loss')
    plt.title('Validation Accuracy Vs Training Loss')
    plt.xlabel('Epochs')
    plt.xticks(arange(1, args.epochs + 1, 1))
    plt.yticks(arange(0, 1.1, 0.1))
    plt.legend(loc='best')
    plt.show()

    for error in errors[-5:]:
        print(valid_data1[error[0]], error[1])

