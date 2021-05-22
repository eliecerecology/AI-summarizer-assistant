from flask import Flask, redirect, url_for, render_template, request, Markup
import os
from operator import itemgetter
import pandas as pd
from collections import Counter
import re
import pdf_parse_functions
import tableparser
from transformers import pipeline
import boto3
import io, os, base64
import matplotlib.pyplot as plt

app = Flask(__name__)
summa = pipeline("summarization")
sentiment_analysis = pipeline('sentiment-analysis')

datapath ='/home/helix/Documents/UNAIDS/code/DemoFlask2/upload_folder/'
pdfnames = os.listdir(datapath)
summaries = []

# Defining the home page of our site
@app.route("/")  # this sets the route to this page
def home():
     return render_template("base.html",)  # some basic inline html

@app.route("/tables", methods=["POST", "GET"])
def tables():
       
    if request.method == "POST":
    
        tabl = request.files["tabla"]
        tabl.save(os.path.join('static/images/', tabl.filename))
        #tabl.save(os.path.join('tables_folder', tabl.filename))
        photonames = os.listdir('static/images/')
        #photonames = os.listdir('/home/helix/Documents/UNAIDS/Development/DemoFlask2/tables_folder/')
        
        return redirect(url_for("table_change", photo = photonames[0]))
    else:
        return render_template("table.html")

#AWS connection and table converter
@app.route("/<photo>", methods=["POST", "GET"])
def table_change(photo):
    path = 'static/images/'+photo
    tableparser.main_conv('static/images/'+photo)
    #tableparser.main_conv('/home/helix/Documents/UNAIDS/Development/DemoFlask2/tables_folder/'+photo)
    return render_template("table_output.html", path = path)
       
@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        
        fil = request.files["filex"]
        fil.save(os.path.join('upload_folder', fil.filename))
        return redirect(url_for("keywords"))
            
    else:
        return render_template("login.html")

@app.route("/keywords", methods=["POST", "GET"])
def keywords():
    if request.method == "POST":
       
        user = request.form["keyword"]
        user1 = request.form["keyword2"]
        return redirect(url_for("user", usr = user, usr1 = user1))
            
    else:
        return render_template("keywords.html")

@app.route("/<usr>, <usr1>")
def user(usr, usr1):
    paragraphs = pdf_parse_functions.pdf_parser(datapath+pdfnames[0])
    paragraphs_with_key_words = pdf_parse_functions.get_paragraphs_with_key_words(paragraphs, (usr, usr1, "sex"))
    global summaries
    lista = []
    summaries = []
    for i in range(0,len(paragraphs_with_key_words)):
          lista.append(paragraphs_with_key_words[i]['text'])
          
          summaries.append(summa(paragraphs_with_key_words[i]['text'])) #remove this for demo
          print(i)
    print("finish!")

    label = []
    score = []
    for i in summaries:
        label = []
    score = []
    for i in summaries:
    
        result = sentiment_analysis((i[0]['summary_text']))[0]
        label.append(result['label'])
        score.append(result['score'])   
    
    data_tuples = list(zip(label,score))
    df = pd.DataFrame(data_tuples, columns=['label','score'])

    posit = df[df["label"] == "POSITIVE"]
    negat = df[df["label"] == "NEGATIVE"]
    means = [posit['score'].mean(), negat['score'].mean() ]
    labe = ["POSITIVE", "NEGATIVE"]

    fig = plt.figure()


    ax = fig.add_axes([1,1,1,1])
    ax.set_ylim([0,1])
    ax.bar(labe, means)
    ax.set_xlabel("sentiment")
    ax.set_title("Article 2")
    ax.set_ylabel("Mean score Latin America")
    

    plt.savefig('static/images/plot.png')

    return render_template("base1.html", text = lista, text1 = summaries, plot = "static/images/plot.png")

#auxilia function
# @app.route("/plot")
# def integration(summaries):
#     label = []
#     score = []
#     for i in summaries:return summaries
#     data_tuples = list(zip(label,score))
#     df = pd.DataFrame(data_tuples, columns=['label','score'])

#     posit = df[df["label"] == "POSITIVE"]
#     negat = df[df["label"] == "NEGATIVE"]
#     means = [posit['score'].mean(), negat['score'].mean() ]
#     labe = ["POSITIVE", "NEGATIVE"]

#     #plt.add_axes([0,0,1,1])
#     plt.set_ylim([0,1])
#     plt.bar(labe, means)
#     plt.set_xlabel("sentiment")
#     plt.set_title("Article 2")
#     plt.set_ylabel("Mean score Latin America")

#     plt.savefig('static/images/plot.png')
	
#     return render_template('integration.html', url='/static/images/plot.png')

# def plot():
#     left = [1, 2, 3, 4, 5]
#     # heights of bars
#     height = [10, 24, 36, 40, 5]
#     # labels for bars
#     tick_label = ['one', 'two', 'three', 'four', 'five']
#     # plotting a bar chart
#     plt.bar(left, height, tick_label=tick_label, width=0.8, color=['red', 'green'])

#     # naming the y-axis
#     plt.ylabel('y - axis')
#     # naming the x-axis
#     plt.xlabel('x - axis')
#     # plot title
#     plt.title('My bar chart!')

#     plt.savefig('static/images/plot.png')

    #return render_template('integration.html', url='/static/images/plot.png')






    
if __name__ == "__main__":
    app.run(debug=True, port=5001, threaded=True)
