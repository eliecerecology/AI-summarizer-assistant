from flask import Flask, redirect, url_for, render_template, request, Markup, flash, jsonify
import io, os, base64
from operator import itemgetter
import pandas as pd
from collections import Counter
import re
import math
import pdf_parse_functions
import tableparser
from transformers import pipeline
import boto3
import matplotlib.pyplot as plt
from pymongo import MongoClient
import datetime
import shutil

app = Flask(__name__)
pop_df = None
location_list = None

client = MongoClient("mongodb://host.docker.internal:27017/")
mydatabase = client["resumenesDB"]
mydatabase.list_collection_names()
mycollection = mydatabase["test"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#Globals
summa = pipeline("summarization")
sentiment_analysis = pipeline('sentiment-analysis')

datapath ='./upload_folder/'
pdfnames = os.listdir(datapath)
summaries = []

@app.before_first_request
def startup():
	global pop_df, location_list

	# load and prepare the data
	pop_df = pd.read_csv('/home/helix/Documents/UNAIDS/Data_sources/WPP2019_PopulationByAgeSex_Medium.csv')
	location_list = sorted(list(set(pop_df['Location'])))

def get_poulation_pyramid(country, year):
	pop_df_tmp = pop_df[(pop_df['Location']==country) & (pop_df['Time']==year)].copy()
	pop_df_tmp = pop_df_tmp.sort_values('AgeGrpStart',ascending=True)
	return(pop_df_tmp)


# Defining the home page of our site
@app.route("/")  # this sets the route to this page
def home():
     return render_template("base.html",)  # some basic inline html

@app.route("/integration")  # this sets the route to this page
def integration():
     return render_template("integration.html",)  # some basic inline html

@app.route("/tables", methods=["POST", "GET"])
def tables():
       
    if request.method == "POST":
    
        tabl = request.files["tabla"]
        tabl.save(os.path.join('static/images/', tabl.filename))
        photonames = os.listdir('static/images/')
        
        return redirect(url_for("table_change", photo = photonames[0]))
    else:
        return render_template("table.html")

#AWS connection and table converter
@app.route("/<photo>", methods=["POST", "GET"])
def table_change(photo):
    path = 'static/images/'+photo
    tableparser.main_conv('static/images/'+photo)
    
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
        country = request.form["country"]
        return redirect(url_for("user", usr = user, usr1 = user1, country = country))
            
    else:
        return render_template("keywords.html")

@app.route("/<usr>, <usr1>, <country>")
def user(usr, usr1, country):
    datapath ='./upload_folder/'
    pdfnames = os.listdir(datapath)
    
    paragraphs = pdf_parse_functions.pdf_parser(datapath+pdfnames[0])
    paragraphs_with_key_words = pdf_parse_functions.get_paragraphs_with_key_words(paragraphs, (usr, usr1, "sex"))
        
    lista = []
    summaries = []
    for i in range(0,len(paragraphs_with_key_words)):
        lista.append(paragraphs_with_key_words[i]['text'])
        summaries.append(summa(paragraphs_with_key_words[i]['text'])) #remove this for demo
        print(i)
       

    print("finish!")
    
    #Uploading data to mongoDB
    
    #use database named "organisation"
    for summary in summaries:
        date = datetime.datetime.now()
        mycollection.insert_one({"country": country, "time": date,  "summary": summary[0]["summary_text"]})
    
    dirpath = 'upload_folder'
    shutil.rmtree(dirpath)
    os.mkdir(dirpath)

    return render_template("base1.html", text = lista, text1 = summaries)

@app.route("/quantitive/", methods=['POST', 'GET'])
def build_pyramid():
    plot_to_show = ''
    selected_country = ''
    country_list = ''
    selected_year = ''
    plot_to_show1 = ''
    
	
    if request.method == 'POST':
	    selected_country = request.form['selected_country']
	    selected_year = int(request.form['selected_year'])
        
    pop_df_tmp = get_poulation_pyramid(selected_country, selected_year)

		
    y = range(0, len(pop_df_tmp))
    x_male = pop_df_tmp['PopMale']
    x_female = pop_df_tmp['PopFemale']

	# max xlim
    fig = plt.figure(figsize=(22, 20))
    
    #fig.patch.set_facecolor('xkcd:white')
    plt.figtext(.5,.9,selected_country + ": " +  str(selected_year), fontsize=35, ha='center')
    
    axes1 = fig.add_subplot(221)
    	
    axes1.barh(y, x_male, align='center', color='blue')
    axes1.tick_params(axis='x', labelsize=18)
    axes1.tick_params(axis='y', labelsize=18)
    axes1.set(title='Males')
    
    axes2 = fig.add_subplot(222)
    axes2.barh(y, x_female, align='center', color='red')
    axes2.set(title='Females')
    
    axes1.set_ylabel('Age class', size = 20)
    axes1.set_xlabel('Number of people', fontsize = 20)
    axes2.set_xlabel('Number of people', size = 20)
    axes2.tick_params(axis='x', labelsize=18)
    axes2.tick_params(axis='y', labelsize=18)
    axes2.grid()

    axes1.set(yticks=y, yticklabels=pop_df_tmp['AgeGrp'])
    axes2.set(yticks=y, yticklabels=pop_df_tmp['AgeGrp'])
    axes1.invert_xaxis() 
    axes1.grid()	

    ##################################
    ################FINANCIAL
    ##################################
    datapath = "/home/helix/Documents/UNAIDS/Data_sources/"
    lawsfile = "NCPI_2020_en.csv"
    # key populations data
    kpfile = "KPAtlasDB_2020_en.csv"
    column_names=('Indicator','Unit','Subgroup','Area','Area ID','Time Period','Source','Data Value')
    kp_data = pd.read_csv(datapath+kpfile, usecols = column_names)
    # NEEDED
    expenditfile = "GARPR16-GAM2020ProgrammeExpenditures.xlsx"
    ex_data = pd.read_excel(datapath+expenditfile)
    ex_data.rename(columns=dict(zip(ex_data.columns[1:10],[str(int(a)) for a in ex_data.iloc[3,1:10]])),inplace=True)
    ex_data.rename(columns={'Reporting cycle':'Countries','Unnamed: 10':'Total'},inplace=True)
    ex_data.drop(labels=[0,1,2,3],axis='index',inplace=True)
    ex_data = ex_data.reset_index(drop=True)

    # epidemic transition metrics
    epidemicfile = "PeopleLivingWithHIV.xlsx"
    ep_data = pd.read_excel(datapath+epidemicfile, dtype=str)

    for year in range(2011,2020):
        for ind in ep_data.index:
            if len(ep_data.loc[ind,str(year)]) > 0:
                x = ep_data.loc[ind,str(year)]
                if re.findall(r"^\d+\s\d*",x):
                    ep_data.loc[ind,str(year)] = float(re.findall(r"^\d+\s\d*",x)[0].replace(" ",""))
                else:
                    ep_data.loc[ind,str(year)] = math.nan
            else:
                ep_data.loc[ind,str(year)] = math.nan

    data = {}
    for country in ex_data['Countries']:
        data[country] = {'years':[],'epdata':[],'exdata':[]}    
        for year in range(2011,2020):
            
            x = ex_data.loc[ex_data['Countries'] == country,str(year)].values
            y = ep_data.loc[ep_data['Country'] == country,str(year)].values
            if x and y and not ( math.isnan(x) or math.isnan(y) ):
                data[country]['years'].append(year)
                data[country]['epdata'].append(y)
                data[country]['exdata'].append(x/1000000)

    # for country in data:
    new = pd.DataFrame([])
    for country in ex_data['Countries']:
        #print(country)
        ne = pd.DataFrame.from_dict(data[country])
        ne['country'] = country
        ne['epdata'] = ne['epdata'].map(lambda x: float(x))
        ne['exdata'] = ne['exdata'].map(lambda x: float(x))
        ne['years'] =  ne['years'].astype(int)
    
        new = pd.concat([new, ne], axis=0)
    
    country = selected_country
    #print(selected_country)
    data = new[new['country'] == selected_country]
    data['epdata'] = data['epdata']/1000
    
    axes4 = fig.add_subplot(224)
    axes4.plot(data.iloc[:, 2], data.iloc[:, 1])
    #axes4.plot(data.iloc[0, 2], data.iloc[0, 1], 'bo', markersize=20)
    #axes4.plot(data.iloc[1:len(data)-1, 2], data.iloc[1:len(data)-1, 1], 'go',markersize=20)
    #axes4.plot(data.iloc[len(data)-1, 2], data.iloc[len(data)-1, 1], 'ro', markersize=20)
    for i in range(0,len(data)):
        axes4.text(data.iloc[i, 2], data.iloc[i, 1], data.iloc[i, 0], size = 15)
        
    axes4.set_xlabel('USD expenditures on HIV prevention [million]',size = 20)
    axes4.set_ylabel('Number of people living with HIV [million]', size = 20)
    axes4.set_title(country, size =22)
    
    ############################
    # Sentiment analyses
    ############################
    stuff = mycollection.find({"country": selected_country})
    
    summaries = []
    for i in stuff:
        summaries.append(i)
    

    label = []
    score = []
    for i in summaries:
        try:
            result = sentiment_analysis((i['summary']))[0]
            #print(j)
            #print(result)
            label.append(result['label'])
            score.append(result['score']) 
        except:
            pass  
    
    data_tuples = list(zip(label, score))
    df = pd.DataFrame(data_tuples, columns=['label','score'])

    posit = df[df["label"] == "POSITIVE"]
    negat = df[df["label"] == "NEGATIVE"]
    means = [posit['score'].mean(), negat['score'].mean() ]
    labe = ["POSITIVE", "NEGATIVE"]
   
    axes3 = fig.add_subplot(223)
    axes3.set_ylim([0,1])
    axes3.bar(labe, means)
    axes3.set_title("Sentiment",size = 20)
    axes3.set_ylabel("Mean score",size = 20)
	
    img = io.BytesIO()
		
    plt.savefig(img, format='png')
		
    img.seek(0)
		
    plot_url = base64.b64encode(img.getvalue()).decode()
		
    plot_to_show = Markup('<img src="data:image/png;base64,{}" style="width:100%;vertical-align:top">'.format(plot_url))
    
    # get from MongoDB
    #use database named "organisation"
    cursorII = mycollection.find({"country": selected_country})

    j = 0
    syntheses = []
    for record in cursorII: 
        syntheses.append(record["summary"])
        print(record["summary"])
        j += 1
        if j == 5:
            break


        
    return render_template('build-a-pyramid.html',
            plot_to_show = plot_to_show,
            selected_country = selected_country,
            location_list = location_list,
            selected_year = selected_year, 
            summary = syntheses
            )
    
if __name__ == "__main__":
    app.run(debug=True, port=5001, threaded=True)
