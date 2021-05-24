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

app = Flask(__name__)
pop_df = None
location_list = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#Globals
summa = pipeline("summarization")
sentiment_analysis = pipeline('sentiment-analysis')

datapath ='/home/helix/Documents/UNAIDS/code/DemoFlask2/upload_folder/'
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

@app.route("/quantitive", methods=['POST', 'GET'])
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
    #max_x_scale = max(max(x_female), max(x_male))
    fig = plt.figure(figsize=(22, 20))
    #fig, (axes1, axes2) = plt.subplots(nrows = 1, ncols =2, sharey=True, figsize=(22, 20))
    
    fig.patch.set_facecolor('xkcd:white')
    plt.figtext(.5,.9,selected_country + ": " +  str(selected_year), fontsize=15, ha='center')

    axes1 = fig.add_subplot(221)
    	
    axes1.barh(y, x_male, align='center', color='lightblue')
    axes1.set(title='Males')
    #axes[0].set(xlim=[0,max_x_scale])
    axes2 = fig.add_subplot(222)
    axes2.barh(y, x_female, align='center', color='pink')
    axes2.set(title='Females')
    #axes[1].set(xlim=[0,max_x_scale])
    axes2.grid()
    		
    axes1.set(yticks=y, yticklabels=pop_df_tmp['AgeGrp'])
    axes1.invert_xaxis()
    axes1.grid()	
    
    ################KK
    datapath = "/home/helix/Documents/UNAIDS/Data_sources/"
    lawsfile = "NCPI_2020_en.csv"
    kpfile = "KPAtlasDB_2020_en.csv"
    column_names=('Indicator','Unit','Subgroup','Area','Area ID','Time Period','Source','Data Value')
    kp_data = pd.read_csv(datapath+kpfile,usecols=column_names)
    expenditfile = "GARPR16-GAM2020ProgrammeExpenditures.xlsx"
    ex_data = pd.read_excel(datapath+expenditfile)
    ex_data.rename(columns=dict(zip(ex_data.columns[1:10],[str(int(a)) for a in ex_data.iloc[3,1:10]])),inplace=True)
    ex_data.rename(columns={'Reporting cycle':'Countries','Unnamed: 10':'Total'},inplace=True)
    ex_data.drop(labels=[0,1,2,3],axis='index',inplace=True)
    ex_data.reset_index(drop=True)

    # epidemic transition metrics
    epidemicfile = "NewHIVinfections.xlsx"
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
    axes3 = fig.add_subplot(223)
    axes3.set_xlim(0,1500)
    axes3.set_ylim(0,175000)

    data = {}
    for country in ex_data['Countries']:
        
        data[country] = {'years':[],'epdata':[],'exdata':[]}    
        for year in range(2011,2020):
            #ep_data[str(year)] = ep_data[str(year)].apply(lambda x: int(re.findall(r"^\d+\s\d*",x)[0].replace(" ","")) 
            #            if len(x)>0 and re.findall(r"^\d+\s\d*",x)
            #            else None)

            x = ex_data.loc[ex_data['Countries']==country,str(year)].values
            y = ep_data.loc[ep_data['Country']==country,str(year)].values
            if x and y and not ( math.isnan(x) or math.isnan(y) ):
                data[country]['years'].append(year)
                data[country]['epdata'].append(y)
                data[country]['exdata'].append(x/1000000)

    for country in data:
        
        if len(data[country]['exdata']) > 0 and len(data[country]['epdata']) > 0:
            axes3.plot(data[country]['exdata'],data[country]['epdata'])
            axes3.plot(data[country]['exdata'][-1],data[country]['epdata'][-1],'ro')
            axes3.text(data[country]['exdata'][-1],data[country]['epdata'][-1],country)

        
    axes3.set_xlabel('Expenditures on HIV prevention (millions USD)')
    axes3.set_ylabel('Number of people living with HIV')

    
		
    img = io.BytesIO()
		
    plt.savefig(img, format='png')
		
    img.seek(0)
		
    plot_url = base64.b64encode(img.getvalue()).decode()
		
    plot_to_show = Markup('<img src="data:image/png;base64,{}" style="width:100%;vertical-align:top">'.format(plot_url))
    
    #plot_to_show1 = k_function(selected_country)

    
    return render_template('build-a-pyramid.html',
            plot_to_show = plot_to_show,
            #plot_to_show1 = plot_to_show1,
            selected_country = selected_country,
            location_list = location_list,
            selected_year = selected_year)





    
if __name__ == "__main__":
    app.run(debug=True, port=5001, threaded=True)
