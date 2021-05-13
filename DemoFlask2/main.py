from flask import Flask, redirect, url_for, render_template, request
import os
from operator import itemgetter
from collections import Counter
import re
import pdf_parse_functions
import tableparser
from transformers import pipeline
import boto3

app = Flask(__name__)
summa = pipeline("summarization")

datapath ='/home/helix/Documents/UNAIDS/code/DemoFlask2/upload_folder/'
pdfnames = os.listdir(datapath)

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
    
    lista = []
    summaries = []
    for i in range(0,len(paragraphs_with_key_words)):
          lista.append(paragraphs_with_key_words[i]['text'])
          
          summaries.append(summa(paragraphs_with_key_words[i]['text'])) #remove this for demo
          print(i)
    print("finish!")
    return render_template("base1.html", text = lista, text1 = summaries)

    
if __name__ == "__main__":
    app.run(debug=True, port=5001, threaded=True)
