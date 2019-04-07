import json
import time
import os
import logging
import urllib
import boto3
from botocore.exceptions import ClientError

import re
import unicodedata

import torch
import torch.nn as nn
import random
import math
import itertools


from vocabulary import Voc
from chatbot_model import EncoderRNN
from chatbot_model import LuongAttnDecoderRNN
from chatbot_model import GreedySearchDecoder

dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')

# Grab the Bot OAuth token from the environment.
MODEL_NAME = os.environ["MODEL_NAME"]

USE_CUDA = torch.cuda.is_available()
device = torch.device("cuda" if USE_CUDA else "cpu")

MAX_LENGTH = 10  # Maximum sentence length to consider
corpus_name = "cornell movie-dialogs corpus"

# Default word tokens
PAD_token = 0  # Used for padding short sentences
SOS_token = 1  # Start-of-sentence token
EOS_token = 2  # End-of-sentence token

def unicodeToAscii(s):
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )

def normalizeString(s):
    s = unicodeToAscii(s.lower().strip())
    s = re.sub(r"([.!?])", r" \1", s)
    s = re.sub(r"[^a-zA-Z.!?]+", r" ", s)
    s = re.sub(r"\s+", r" ", s).strip()
    return s

def indexesFromSentence(voc, sentence):
    return [voc.word2index[word] for word in sentence.split(' ')] + [EOS_token]

def evaluate(encoder, decoder, searcher, voc, sentence, max_length=MAX_LENGTH):
    ### Format input sentence as a batch
    # words -> indexes
    indexes_batch = [indexesFromSentence(voc, sentence)]
    # Create lengths tensor
    lengths = torch.tensor([len(indexes) for indexes in indexes_batch])
    # Transpose dimensions of batch to match models' expectations
    input_batch = torch.LongTensor(indexes_batch).transpose(0, 1)
    # Use appropriate device
    input_batch = input_batch.to(device)
    lengths = lengths.to(device)
    # Decode sentence with searcher
    tokens, scores = searcher(input_batch, lengths, max_length)
    # indexes -> words
    decoded_words = [voc.index2word[token.item()] for token in tokens]
    return decoded_words


def evaluateInput(encoder, decoder, searcher, voc, sentence):
    input_sentence = ''
    try:
        # Get input sentence
        input_sentence = sentence
        # Normalize sentence
        input_sentence = normalizeString(input_sentence)
        # Evaluate sentence
        output_words = evaluate(encoder, decoder, searcher, voc, input_sentence)
        # Format and print response sentence
        output_words[:] = [x for x in output_words if not (x == 'EOS' or x == 'PAD')]
        print('Bot:', ' '.join(output_words))

    except KeyError:
        print("i don't know what you mean")
        
    return(' '.join(output_words))

def build_model():
    # Configure models
    model_name = 'cb_model'
    attn_model = 'dot'
    hidden_size = 500
    encoder_n_layers = 2
    decoder_n_layers = 2
    dropout = 0.1
    batch_size = 64
    voc = Voc(corpus_name)

    # Set checkpoint to load from; set to None if starting from scratch
    loadFilename = os.path.join('/tmp/', MODEL_NAME)

    # If loading on same machine the model was trained on
    # If loading a model trained on GPU to CPU
    checkpoint = torch.load(loadFilename, map_location=torch.device('cpu'))
    encoder_sd = checkpoint['en']
    decoder_sd = checkpoint['de']
    encoder_optimizer_sd = checkpoint['en_opt']
    decoder_optimizer_sd = checkpoint['de_opt']
    embedding_sd = checkpoint['embedding']
    voc.__dict__ = checkpoint['voc_dict']


    print('Building encoder and decoder ...')
    # Initialize word embeddings
    embedding = nn.Embedding(voc.num_words, hidden_size)
    embedding.load_state_dict(embedding_sd)
    # Initialize encoder & decoder models
    encoder = EncoderRNN(hidden_size, embedding, encoder_n_layers, dropout)
    decoder = LuongAttnDecoderRNN(attn_model, embedding, hidden_size, voc.num_words, decoder_n_layers, dropout)
    encoder.load_state_dict(encoder_sd)
    decoder.load_state_dict(decoder_sd)
    # Use appropriate device
    encoder = encoder.to(device)
    decoder = decoder.to(device)
    print('Models built and ready to go!')
    return(encoder, decoder, voc)

def chatbot(input_text):
    print("bla")
    if os.path.isfile('/tmp/' + MODEL_NAME) != True:
        try:
            s3.download_file('chatbot-mark', 'chatbot-model/negative-trained-weights/' + MODEL_NAME, '/tmp/' + MODEL_NAME)
            print("complete")
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
            	print("The object does not exist")
            else:
            	raise
    
    encoder, decoder, voc = build_model()
    
    # Set dropout layers to eval mode
    encoder.eval()
    decoder.eval()

    # Initialize search module
    searcher = GreedySearchDecoder(encoder, decoder)
    
    # Evaluate input text
    output_text = evaluateInput(encoder, decoder, searcher, voc, input_text)
     
    return(output_text)

def lambda_handler(event, context):
    print(event)
    
    text = event['Message']
    
    print(text)
    bot_text = chatbot(text)
    print(bot_text)

    # TODO implement
    current_milli_time = lambda: int(round(time.time() * 1000))
    current_time = current_milli_time()

    dynamodb.put_item(
        TableName = 'chat-messages',
        Item = {
            "conversationId": {'S': event['id']},
            "timeStamp": {'N': str(current_time)},
            "Message": {'S': bot_text},
            "Sender": {'S': 'Bot Harry'}
        }
    )
    return("200")
        