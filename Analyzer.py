# import Flask Libraries
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import render_template
from flask import request

#import python libraries
import urllib2
import operator
import re
import json
import time
import ast
import plotly
import psycopg2
import pandas as pd
from datetime import datetime,timedelta

#Initialze the application
app = Flask(__name__)

#Connection to Relational Data base Postgresql
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Dh00mketu@localhost:5432/Analyzer'
app.debug=True
db=SQLAlchemy(app)

#Connection to plotly
plotly.tools.set_credentials_file(username='DeependraSinghJhala', api_key='g4a8ast2d0')

# App Key to access Facebook Graph API
app_id = ""
app_secret = "" # DO NOT SHARE WITH ANYONE!
access_token = app_id + "|" + app_secret

#variable to store user Inputs & db table name
page_id = ""
tablename=""

# flags
flag = 0
graphflag=0

# Create Data Base Connection
hostname = 'localhost'
username = 'postgres'
password = 'Dh00mketu'
database = 'postgres'
myConnection = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
cur = myConnection.cursor()

# This Function fetches  data from given URL &  returns it in JSON Format
def GetInitialPageData(url):
    print url
    req = urllib2.Request(url)
    success = False
    while success is False:
        try:
            response = urllib2.urlopen(req)
            if response.getcode() == 200:
                success = True
        except Exception, e:
            print e
            time.sleep(5)
            print "Error for URL "

    return response.read()

# This Function makes multiple calls to GetInitialPageData() in order to retrieve complete page data in JSON
#format
def GetCompletePageData(page_id, access_token,days):
    days_to_subtract = days
    d = str(datetime.today() - timedelta(days=days_to_subtract))
    d = d[0:10].translate(None, "-")
    d = int(d)
    print d
    base = "https://graph.facebook.com/v2.8"
    node = "/" + page_id + "/posts"  # changed
    parameters = "/?access_token=%s" % access_token
    url = base + node + parameters
    print url
    # retrieve data
    data = {'data': [], 'paging': {"previous": "", "next": ""}}
    kdata = json.loads(GetInitialPageData(url))
    kdata = ast.literal_eval(json.dumps(kdata))

    i = len(kdata['data'])
    j = 0
    while (j != i):
        g = int(kdata['data'][j]["created_time"][0:10].replace("-", ""))
        print g
        if g >= d:
            print "...."
            print g
            data['data'].append(kdata['data'][j])
            j += 1
        else:
            print "inside else"
            return frame(data)
    data["paging"] = kdata["paging"]
    print "i am here"
    fdata = data
    #    l=len(fdata['data'])
    next_page = True
    while (next_page):
        if 'paging' in fdata.keys():
            vdata = json.loads(GetInitialPageData(fdata['paging']['next']))
            i = len(vdata['data'])
            j = 0
            while (j != i):
                g = int(vdata['data'][j]["created_time"][0:10].replace("-", ""))
                if g >= d:

                    data['data'].append(vdata['data'][j])
                    j += 1
                else:
                    print "inside else"
                    return frame(data)
                    break

            fdata = vdata

        else:
            print "looking for issue"
            print data
            next_page = False
    #Returning complete page data in Json Format
    return frame(data)

# This functions makes multiple calls to GetInitialPageData() and returns the Countrywise
# Fans data in json format
def fandata(page_id,access_token,days):
    print "getting fan data"
    days_to_subtract = days
    date_1 = str(datetime.today() - timedelta(days=days_to_subtract))
    date_1 = str(date_1)[0:10].translate(None, '-')
    fromdate = date_1[6:] + "/" + date_1[4:6] + "/" + date_1[0:4]
    print date_1

    date_2 = str(datetime.today() - timedelta(days=1))[0:10]
    date_2 = date_2.translate(None, '-')
    todate = date_2[6:] + "/" + date_2[4:6] + "/" + date_2[0:4]
    print date_2

    p = time.mktime(datetime.strptime(fromdate, "%d/%m/%Y").timetuple())
    q = time.mktime(datetime.strptime(todate, "%d/%m/%Y").timetuple())
    print p
    print q

    print("This is fan D:")
    base = "https://graph.facebook.com/v2.8"
    node = "/" + page_id + "/insights/page_fans_country/lifetime?debug=all&method=get&pretty=0&suppress_http_code=1&since=%d&until=%d" %(p,q)# changed
    parameters = "&access_token=%s" % access_token
    url = base + node + parameters
    data= json.loads(GetInitialPageData(url))
    print data
    data=ast.literal_eval(json.dumps(data))
    return fanframe(data)

# This Function receives Country Wise Fans data in Json format and stores it into pandas dataframe
def fanframe(data):
    length=len(data["data"][0]["values"])
    k=0
    df = pd.DataFrame(
        columns=['time','country','fancount'])
    while k<length:
        fancon=[]
        date = data["data"][0]["values"][k]['end_time']
        date = date[0:10].translate(None, '-')
        for key in data["data"][0]["values"][k]['value']:
            #adding date to list
            fancon.append(date)
            fancon.append(key)
            fancon.append(data["data"][0]["values"][k]['value'][key])
            s = pd.Series(fancon,
                          index=['time','country','fancount'])

            df = df.append(s, ignore_index=True)
            fancon=[]
        k+=1
    return df

# This function takes dataframe containing coutrywise fans data & stores it into postgresql database
def store_fancount(frame):
    fantable=tablename+"fans"
    names=frame.columns
    bracketed_names = ['"' + column + '"' for column in names]
    col_names = ','.join(bracketed_names)
    wildcards = ','.join([r'%s'] * len(names))
    insert_query = 'INSERT INTO %s (%s) VALUES (%s)' % (
        fantable, col_names, wildcards)
    data = [tuple(x) for x in frame.values]
    myConnection = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
    cur = myConnection.cursor()
    cur.executemany(insert_query, data)
    myConnection.commit()

# This Function makes multiple calls to GetInitialPageData & retrieves the all data related
# to Vistor's post (posts where page has been tagged) in JSON Format
def taggedpost(page_id, access_token,days):
    days_to_subtract = days
    d = str(datetime.today() - timedelta(days=days_to_subtract))
    d = d[0:10].translate(None, "-")
    d = int(d)
    print("This is D:")
    print d
    base = "https://graph.facebook.com/v2.8"
    node = "/" + page_id + "/tagged"  # changed
    parameters = "/?access_token=%s" % access_token
    url = base + node + parameters
    print url
    # retrieve data
    data = {'data': [], 'paging': {"previous": "", "next": ""}}
    kdata = json.loads(GetInitialPageData(url))
    kdata = ast.literal_eval(json.dumps(kdata))

    i = len(kdata['data'])
    if i==0:
        global graphflag
        print "Problem1"
        graphflag=1
    j = 0
    while (j != i):
        g = int(kdata['data'][j]["tagged_time"][0:10].replace("-", ""))
        print g
        if g >= d:
            print "...."
            print g
            data['data'].append(kdata['data'][j])
            j += 1

        else:
            print "inside else"
            return frame(data)
    try:
        data["paging"] = kdata["paging"]
    except:
        global graphflag
        print "Problem2"
        graphflag=1
        return
    print "i am here"
    fdata = data
    #    l=len(fdata['data'])
    next_page = True
    while (next_page):
        if 'paging' in fdata.keys():
            vdata = json.loads(GetInitialPageData(fdata['paging']['next']))
            i = len(vdata['data'])
            j = 0
            while (j != i):
                g = int(vdata['data'][j]["tagged_time"][0:10].replace("-", ""))
                if g >= d:
                    data['data'].append(vdata['data'][j])
                    j += 1
                    print "adding Values"
                else:
                    print "inside else of dsfk"
                    print data

                    return frame(data)
                    break

            fdata = vdata

        else:
            next_page = False
    return frame(data)


# This Function takes Page's post data in JSON format & stores it to pandas dataframe
def frame(data):
    listid = []
    for x in data["data"]:
        listid.append(x["id"])
    l = len(listid)
    print "length"
    print l
    df = pd.DataFrame(
        columns=['id', 'link', 'typ','category', 'message','story', 'created_time', 'shares', 'comments', 'likes', 'love', 'haha', 'wow',
                 'sad', 'angry','emotion'])

    o = 0

    p = l / 50
    m = l % 50
    u = 50

    while (p >= 0):

        if p == 0:
            u = m + o
        if l <= 50:
            u = l
            p = 0
            m = 0
        print "o=%d to u=%d" % (o, u)
        print "p==%d" % (p)
        url = "https://graph.facebook.com/v2.8/?ids="
        for ids in listid[o:u]:
            url = url + ids + ","
        x = len(url) - 1



        #changes done here
        url = url[
              0:x] + "&fields=id,link,type,message,story,created_time,shares,comments.limit(0).summary(total_count),reactions.type(LIKE).limit(0).summary(total_count).as(reactions_like),reactions.type(LOVE).limit(0).summary(total_count).as(reactions_love),reactions.type(WOW).limit(0).summary(total_count).as(reactions_wow),reactions.type(HAHA).limit(0).summary(total_count).as(reactions_haha),reactions.type(SAD).limit(0).summary(total_count).as(reactions_sad),reactions.type(ANGRY).limit(0).summary(total_count).as(reactions_angry)&access_token=1774340462813774|806f62247d55390ef50528a17c5fb514"
        print url
        next_page = True
        datalist = []
        data = json.loads(GetInitialPageData(url))
        data = ast.literal_eval(json.dumps(data))
        print "length:"
        y = 0
        for x in data:
            y += 1
        print y

        for posts in data:
            idd="D"+data[posts]["id"]
            idd=idd.split('_', 1)[-1]
            datalist.append(idd)
            try:
                datalist.append(data[posts]["link"])
            except:
                datalist.append("None")

            datalist.append(data[posts]["type"])

            if data[posts]["type"] == 'video':
                nurl="https://graph.facebook.com/v2.8/"+data[posts]["id"]+"?fields=link&access_token=1774340462813774|806f62247d55390ef50528a17c5fb514"
                tdata=json.loads(GetInitialPageData(nurl))
                tdata = ast.literal_eval(json.dumps(tdata))
                kkk=tdata["link"]
                if 'facebook' in kkk:
                    try:
                        ks=kkk.split("videos/", 1)[1]
                        nurl = "https://graph.facebook.com/v2.8/" + ks + "?fields=content_category&access_token=1774340462813774|806f62247d55390ef50528a17c5fb514"
                        tdata = json.loads(GetInitialPageData(nurl))
                        tdata = ast.literal_eval(json.dumps(tdata))
                        category = tdata['content_category']
                        datalist.append(category)
                    except:
                        datalist.append("None")
                else:
                    datalist.append("None")
            else:
                datalist.append("None")



            try:

                messag = data[posts]["message"]
                messag=re.sub(r'([^\s\w]|_)+', '', messag)
                datalist.append(messag)

            except:
                datalist.append("None")

            try:
                storye = data[posts]["story"]
                storye = re.sub(r'([^\s\w]|_)+', '', storye)
                datalist.append(storye)

            except:
                datalist.append("None")
            da=data[posts]["created_time"]
            da=da[0:10].translate(None, "-")
            datalist.append(da)

            try:
                datalist.append(data[posts]["shares"]["count"])
            except:
                datalist.append(0)

            try:
                datalist.append(data[posts]["comments"]["summary"]["total_count"])
            except:
                datalist.append(0)

            try:
                datalist.append(data[posts]["reactions_like"]["summary"]["total_count"])
            except:
                datalist.append(0)

            dict1={}
            dict2={}

            try:
                rlove=data[posts]["reactions_love"]["summary"]["total_count"]
                datalist.append(rlove)
                dict1["love"] = rlove
                dict2["love"] = rlove
            except:
                datalist.append(0)

            try:
                rhaha=data[posts]["reactions_haha"]["summary"]["total_count"]
                datalist.append(rhaha)
                dict1["haha"] = rhaha
                dict2["haha"] = rhaha
            except:
                datalist.append(0)

            try:
                rwow=data[posts]["reactions_wow"]["summary"]["total_count"]
                datalist.append(rwow)
                dict1["wow"] = rwow
                dict2["wow"] = rwow
            except:
                datalist.append(0)

            try:
                rsad=data[posts]["reactions_sad"]["summary"]["total_count"]
                datalist.append(rsad)
                dict1["sad"] = rsad
                dict2["sad"] = rsad
            except:
                datalist.append(0)

            try:
                rangry = data[posts]["reactions_angry"]["summary"]["total_count"]
                datalist.append(rangry)
                dict1["angry"] = rangry
                dict2["angry"] = rangry
            except:
                datalist.append(0)

            lar = max(dict1.iteritems(), key=operator.itemgetter(1))[0]
            print lar
            print dict2
            del dict1[lar]
            slar = max(dict1.iteritems(), key=operator.itemgetter(1))[0]
            print slar
            e1 = lar
            e2 = slar
            if dict2[slar] <= dict2[lar] / 2:


                if e1 == "love" and e2 == "haha":
                    emotion = "positive"
                if e1 == "love" and e2 == "wow":
                    emotion = "positive"
                if e1 == "love" and e2 == "sad":
                    emotion = "negative"
                if e1 == "love" and e2 == "angry":
                    emotion = "negative"
                if e1 == "haha" and e2 == "love":
                    emotion = "positive"
                if e1 == "haha" and e2 == "wow":
                    emotion = "positive"
                if e1 == "haha" and e2 == "sad":
                    emotion = "positive"
                if e1 == "haha" and e2 == "angry":
                    emotion = "positive"
                if e1 == "wow" and e2 == "love":
                    emotion = "positive"
                if e1 == "wow" and e2 == "haha":
                    emotion = "positive"
                if e1 == "wow" and e2 == "sad":
                    emotion = "negative"
                if e1 == "wow" and e2 == "angry":
                    emotion = "negative"
                if e1 == "sad" and e2 == "love":
                    emotion = "negative"
                if e1 == "sad" and e2 == "haha":
                    emotion = "negative"
                if e1 == "sad" and e2 == "wow":
                    emotion = "negative"
                if e1 == "sad" and e2 == "angry":
                    emotion = "negative"
                if e1 == "angry" and e2 == "love":
                   emotion = "negative"
                if e1 == "angry" and e2 == "haha":
                   emotion = "negative"
                if e1 == "angry" and e2 == "wow":
                   emotion = "negative"
                if e1 == "angry" and e2 == "sad":
                   emotion = "negative"
            else:
                if e1=="love":
                    emotion = "positive"
                if e1=="haha":
                    emotion = "positive"
                if e1 == "wow":
                    emotion = "positive"
                if e1=="sad":
                    emotion="negative"
                if e1=="angry":
                    emotion="negative"



            datalist.append(emotion)
            print datalist
            s = pd.Series(datalist,
                          index=['id', 'link', 'typ','category', 'message','story', 'created_time', 'shares', 'comments', 'likes', 'love',
                                 'haha', 'wow', 'sad', 'angry','emotion'])

            df = df.append(s, ignore_index=True)
            datalist = []

        p -= 1
        o = o + 50
        u = u + 50
    return df

# This function stores dataframe containing page's posts to RDBMS- Postgresql
def store_pageposts(frame):
    print "storing page posts"
    names=frame.columns
    bracketed_names = ['"' + column + '"' for column in names]
    col_names = ','.join(bracketed_names)
    wildcards = ','.join([r'%s'] * len(names))
    insert_query = 'INSERT INTO %s (%s) VALUES (%s)' % (
        tablename, col_names, wildcards)
    data = [tuple(x) for x in frame.values]
    myConnection = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
    cur = myConnection.cursor()
    cur.executemany(insert_query, data)
    myConnection.commit()

# This function stores dataframe containing visitor's posts to Postgresql db
def store_visitorposts(frame):
    print "storing visitor post"
    table2=tablename+"visitor"
    try:
        names=frame.columns
    except:
        global graphflag
        print "Problem3"
        graphflag=1
        return
    bracketed_names = ['"' + column + '"' for column in names]
    col_names = ','.join(bracketed_names)
    wildcards = ','.join([r'%s'] * len(names))
    insert_query = 'INSERT INTO %s (%s) VALUES (%s)' % (
        table2, col_names, wildcards)
    data = [tuple(x) for x in frame.values]
    myConnection = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
    cur = myConnection.cursor()
    cur.executemany(insert_query, data)
    myConnection.commit()

# This function fetchs data from postgresql db & creates graph for the pages which contains both page posts
#& visitor posts (for many pages there are no visitors posting so we need to consider them separately)
def graph(daydiff):
    global graphflag

    if graphflag==0:
        #Graph 1 Postings Related to page
        table2 = tablename + "visitor"
        list1=[]
        label1=["PagePosts","VisitorPosts"]
        #counting no. of rows in pagepost table
        s= 'SELECT COUNT(*) FROM ' + tablename
        myConnection = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
        cur = myConnection.cursor()
        cur.execute(s)
        rows=cur.fetchall()

        ppostnum = int(str(rows[0]).translate(None, '[,() ] L'))

        #counting no. of rows in visitor's post table
        s= 'SELECT COUNT(*) FROM ' + table2
        myConnection = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
        cur = myConnection.cursor()
        cur.execute(s)
        rows=cur.fetchall()
        vpostnum = int(str(rows[0]).translate(None, '[,() ] L'))

        list1.append(ppostnum)
        list1.append(vpostnum)


        #graph 2 Distribution of posts
        first=[]
        second=[]

        #get types of posts posted by page
        s = 'SELECT Distinct typ FROM ' + tablename
        myConnection = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
        cur = myConnection.cursor()
        cur.execute(s)
        rows = cur.fetchall()
        list2 = []
        for r in rows:
            r = str(r).translate(None, '[,() ]')
            list2.append(r)
        #Count Types
        for x in list2:
            # Post distribution
            s = "SELECT COUNT(id) from " + tablename + " where typ=%s" % (x)
            cur.execute(s)
            i = int(str(cur.fetchall()).translate(None, '[,(). L ]'))
            first.append(i)

        #get types of posts posted by visitors
        s = 'SELECT Distinct typ FROM ' + table2
        myConnection = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
        cur = myConnection.cursor()
        cur.execute(s)
        rows = cur.fetchall()
        list3 = []
        for r in rows:
            r = str(r).translate(None, '[,() ]')
            list3.append(r)
        #Count Types
        for x in list3:
            # Post distribution
            s = "SELECT COUNT(id) from " + table2 + " where typ=%s" % (x)
            cur.execute(s)
            i = int(str(cur.fetchall()).translate(None, '[,(). L ]'))
            second.append(i)

        # Reactions based on page post type
        third=[]
        for x in list2:
            s = "SELECT SUM(likes),SUM(love),SUM(haha),SUM(wow),SUM(sad),SUM(angry),sum(shares),sum(comments) FROM " + tablename + " where typ=%s" % (x)
            cur.execute(s)
            paget = list(cur.fetchall())

            j = int(sum(paget[0]))
            third.append(j)

        # Reactions based on visitor post type
        fourth=[]
        for x in list3:
            s = "SELECT SUM(likes),SUM(love),SUM(haha),SUM(wow),SUM(sad),SUM(angry),sum(shares),sum(comments) FROM " + table2 + " where typ=%s" % (x)
            cur.execute(s)
            visitt = list(cur.fetchall())
            if len(visitt)==0:
                visitt=['0','0']

            j = int(sum(visitt[0]))
            fourth.append(j)

        # Overall Reactions on page posts
            s = "SELECT SUM(likes),SUM(love),SUM(haha),SUM(wow),SUM(sad),SUM(angry),sum(shares),sum(comments) FROM " + tablename
            cur.execute(s)
            paget=list(cur.fetchall())

        # Overall Reactions on visitor posts
            s = "SELECT SUM(likes),SUM(love),SUM(haha),SUM(wow),SUM(sad),SUM(angry),sum(shares),sum(comments) FROM " + table2
            cur.execute(s)

            visitt=list(cur.fetchall())
            if len(visitt)==0:
                visitt=['0','0']


        # Reactions
        x=0
        lks = []
        lov = []
        hah = []
        wo=[]
        sa=[]
        an=[]
        sh=[]
        com=[]
        tarikh=[]

        days_to_subtract = daydiff
        dat1 = datetime.today() - timedelta(days=days_to_subtract)
        days=daydiff


        while days >= 0:

            temp = str(dat1)
            temp = str(temp[0:10].translate(None, "-"))
            temp = int(temp)

            s = "SELECT SUM(likes)FROM " +tablename+ " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            ke = list(cur.fetchall())
            lks.append(ke[0][0])

            s = "SELECT SUM(love)FROM "+tablename+" where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            lov.append(lo[0][0])

            s = "SELECT SUM(haha)FROM " +tablename+ " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            hah.append(lo[0][0])

            s = "SELECT SUM(wow)FROM " +tablename+ " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            wo.append(lo[0][0])

            s = "SELECT SUM(sad)FROM "+tablename+" where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            sa.append(lo[0][0])

            s = "SELECT SUM(angry)FROM "+tablename+" where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            an.append(lo[0][0])

            s = "SELECT SUM(shares)FROM "+tablename+" where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            sh.append(lo[0][0])

            s = "SELECT SUM(comments)FROM "+tablename+" where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            com.append(lo[0][0])

            z = temp
            tarikh.append(str(z))
            dat1 = dat1 + timedelta(days=1)
            days -= 1

        tarikh2=[]
        for x in tarikh:
            y=y=x[0:4]+'/'+x[4:6]+"/"+x[6:]
            tarikh2.append(y)


        for x in range(len(lks)):
            if lks[x]==None:
                lks[x]=0

        for x in range(len(lov)):
            if lov[x]==None:
                lov[x]=0

        for x in range(len(hah)):
            if hah[x]==None:
                hah[x]=0

        for x in range(len(wo)):
            if wo[x]==None:
                wo[x]=0

        for x in range(len(sa)):
            if sa[x]==None:
                sa[x]=0

        for x in range(len(an)):
            if an[x]==None:
                an[x]=0

        for x in range(len(sh)):
            if sh[x]==None:
                sh[x]=0

        for x in range(len(com)):
            if com[x]==None:
                com[x]=0

        #Reactions from Visitor Postings
        days_to_subtract = daydiff
        dat1 = datetime.today() - timedelta(days=days_to_subtract)
        days=daydiff

        x = 0
        vlks = []
        vlov = []
        vhah = []
        vwo = []
        vsa = []
        van = []
        vsh = []
        vcom = []
        vtarikh = []

        while days >= 0:

            temp = str(dat1)
            temp = str(temp[0:10].translate(None, "-"))
            temp = int(temp)

            s = "SELECT SUM(likes)FROM " + table2 + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            ke = list(cur.fetchall())
            vlks.append(ke[0][0])

            s = "SELECT SUM(love)FROM " + table2 + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            vlov.append(lo[0][0])

            s = "SELECT SUM(haha)FROM " + table2 + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            vhah.append(lo[0][0])

            s = "SELECT SUM(wow)FROM " + table2 + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            vwo.append(lo[0][0])

            s = "SELECT SUM(sad)FROM " + table2 + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            vsa.append(lo[0][0])

            s = "SELECT SUM(angry)FROM " + table2 + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            van.append(lo[0][0])

            s = "SELECT SUM(shares)FROM " + table2 + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            vsh.append(lo[0][0])

            s = "SELECT SUM(comments)FROM " + table2 + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            vcom.append(lo[0][0])

            z = temp
            vtarikh.append(str(z))
            dat1 = dat1 + timedelta(days=1)
            days -= 1



        vtarikh2 = []
        for x in vtarikh:
            y = y = x[0:4] + '/' + x[4:6] + "/" + x[6:]
            vtarikh2.append(y)
        for x in range(len(vlks)):
            if vlks[x] == None:
                vlks[x] = 0

        for x in range(len(vlov)):
            if vlov[x] == None:
                vlov[x] = 0

        for x in range(len(vhah)):
            if vhah[x] == None:
                vhah[x] = 0

        for x in range(len(vwo)):
            if vwo[x] == None:
                vwo[x] = 0

        for x in range(len(vsa)):
            if vsa[x] == None:
                vsa[x] = 0

        for x in range(len(van)):
            if van[x] == None:
                van[x] = 0

        for x in range(len(vsh)):
            if vsh[x] == None:
                vsh[x] = 0

        for x in range(len(vcom)):
            if vcom[x] == None:
                vcom[x] = 0


        # no. of posts graph
        ndates=[]
        visitposts=[]
        pageposts=[]
        days_to_subtract = daydiff
        dat1 = datetime.today() - timedelta(days=days_to_subtract)
        days=daydiff



        while days >= 0:

            temp = str(dat1)
            temp = str(temp[0:10].translate(None, "-"))
            temp = int(temp)

            s = "SELECT COUNT(*)FROM " + tablename + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            pageposts.append(lo[0][0])

            s = "SELECT COUNT(*)FROM " + table2 + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())

            visitposts.append(lo[0][0])

            z = temp
            ndates.append(str(z))
            dat1 = dat1 + timedelta(days=1)
            days -= 1


        ndates2 = []
        for x in ndates:
            y = x[0:4] + '/' + x[4:6] + "/" + x[6:]
            ndates2.append(y)

        # Fan Count
        fandates=[]
        fancountry=[]
        fannum=[]
        table3=tablename+"fans"

        s = "SELECT DISTINCT time FROM " + table3 + " ORDER BY time ASC"
        cur = myConnection.cursor()
        cur.execute(s)
        lo = list(cur.fetchall())
        for x in lo:
            s=int(x[0])
            fandates.append(s)

        s = "SELECT DISTINCT country FROM " + table3 + " ORDER BY country ASC"
        cur = myConnection.cursor()
        cur.execute(s)
        lo = list(cur.fetchall())
        for y in lo:
            x=str(y[0])
            x=x.translate(None,"')(, ")
            fancountry.append(x)


        brave={}
        for x in fancountry:
            s = "SELECT  fancount FROM " + table3 + " where country = '%s' " %x
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            for xy in lo:
                ov=str(xy)
                uv=int(ov.translate(None,"(,)"))
                fannum.append(uv)
            brave[x]=fannum
            fannum=[]

        print brave

        fandates2=[]
        for x in fandates:
            x=str(x)
            y = x[0:4] + '/' + x[4:6] + "/" + x[6:]
            fandates2.append(y)

        print fandates2

        braver = dict(data=[ ],layout=dict(title="Fans Graph", xaxis=dict(title = 'Day'), yaxis=dict(title = 'Fan Count')))

        for key in brave:
            rt=dict(x=fandates2, y=brave[key], type='Scatter', name=key, line = dict(width = 2,))
            braver["data"].append(rt)
        print  braver

        #Creating Graphs using plotly
        graphs = [
           dict(data=[dict(labels=label1, values=list1, type='pie')], layout=dict(title="Total Page Posts")),
            dict(data=[
                dict(x=ndates2, y=pageposts, type='bar', name='No. of page pageposts'),
                dict(x=ndates2, y=visitposts, type='bar', name="No. of Visitor posts ")],
                layout=dict(title="No. of Posts", barmode="group")),

              dict(data=[dict(labels=list2, values=first, type='pie', domain={"x": [0, .48]}, ),
                       dict(labels=list3, values=second, type='pie', domain={"x": [0.52, 1]}, )],
                 layout=dict(title="Page Posts and Visitor's Posts Distribution"), annotations=[
                    {
                        "font": {
                            "size": 100
                        },
                        "showarrow": False,
                        "text": "VisitorPost",
                        "x": 0.2,
                        "y": 0.5
                    }, {
                        "font": {
                            "size": 100
                        },
                        "showarrow": False,
                        "text": "PagePost",
                        "x": 0.8,
                        "y": 0.5
                    }], ),

           dict(data=[dict(x=list2, y=third, type='bar',name='PagePosts'),dict(x=list3, y=fourth, type='bar',name="VisitorPosts" )], layout=dict(title="Reactions",barmode="group")),

           dict(data=[dict(x=['likes','love','haha','wow','sad','angry','shares','comments'], y=paget[0], type='bar', name='ForPagePosts'),
                       dict(x=['likes','love','haha','wow','sad','angry','shares','comments'], y=visitt[0], type='bar', name="ForVisitorPosts")],
                 layout=dict(title="Reactions Distribution", barmode="group")),



           dict(data=[dict(x=tarikh2, y=lks, type='Scatter', name='likes', line = dict(width = 2,)),
                       dict(x=tarikh2, y=lov, type='Scatter', name="loves", line = dict(width = 2,)),
                       dict(x=tarikh2, y=hah, type='Scatter', name="haha", line = dict(width = 2,)),
                       dict(x=tarikh2, y=wo, type='Scatter', name="wow", line = dict(width = 2,)),
                       dict(x=tarikh2, y=sa, type='Scatter', name="sad", line = dict(width = 2,)),
                       dict(x=tarikh2, y=an, type='Scatter', name="angry", line = dict(width = 2,)),
                       dict(x=tarikh2, y=sh, type='Scatter', name="shares", line = dict(width = 2,)),
                       dict(x=tarikh2, y=com, type='Scatter', name="comments", line = dict(width = 2,)), ],
                       layout=dict(title="Reactions over time from page posts", xaxis=dict(title = 'Day'), yaxis=dict(title = 'Reactions'))),


           dict(data=[
               dict(x=vtarikh2, y=vlks, type='Scatter', name='likes', line=dict(width=2, )),
               dict(x=vtarikh2, y=vlov, type='Scatter', name="loves", line=dict(width=2, )),
               dict(x=vtarikh2, y=vhah, type='Scatter', name="haha", line=dict(width=2, )),
               dict(x=vtarikh2, y=vwo, type='Scatter', name="wow", line=dict(width=2, )),
               dict(x=vtarikh2, y=vsa, type='Scatter', name="sad", line=dict(width=2, )),
               dict(x=vtarikh2, y=van, type='Scatter', name="angry", line=dict( width=2, )),
               dict(x=vtarikh2, y=vsh, type='Scatter', name="shares", line=dict( width=2, )),
               dict(x=vtarikh2, y=vcom, type='Scatter', name="comments",
                   line=dict(color=('rgb(255, 0, 255)'), width=2, )), ],
                layout=dict(title="Reactions over time from Visitor's posts", xaxis=dict(title='Day'),
                            yaxis=dict(title='Reactions'))),

        ]
        graphs.append(braver)


        ids = ['graph-{}'.format(i) for i, _ in enumerate(graphs)]
        graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)

#        s = "Drop table " + tablename
#        cur.execute(s)
#        myConnection.commit()

#        s = "Drop table " + table2
#        cur.execute(s)
#        myConnection.commit()


#        s = "Drop table " + table3
#        cur.execute(s)
#        myConnection.commit()
        return render_template('graph.html',
                               ids=ids,
                               graphJSON=graphJSON)
    else:
        #draw graphs for pages which contains only page postings
        # Graph 1 Postings Related to page
        list1 = []
        label1 = ["PagePosts"]
        # counting no. of rows in pagepost table
        s = 'SELECT COUNT(*) FROM ' + tablename
        myConnection = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
        cur = myConnection.cursor()
        cur.execute(s)
        rows = cur.fetchall()

        ppostnum = int(str(rows[0]).translate(None, '[,() ] L'))
        list1.append(ppostnum)

        # graph 2 Distribution of posts
        first = []
        second = []

        # get types of posts posted by page
        s = 'SELECT Distinct typ FROM ' + tablename
        myConnection = psycopg2.connect(host=hostname, user=username, password=password, dbname=database)
        cur = myConnection.cursor()
        cur.execute(s)
        rows = cur.fetchall()
        list2 = []
        for r in rows:
            r = str(r).translate(None, '[,() ]')
            list2.append(r)
        # Count Types
        for x in list2:
            # Post distribution
            s = "SELECT COUNT(id) from " + tablename + " where typ=%s" % (x)
            cur.execute(s)
            i = int(str(cur.fetchall()).translate(None, '[,(). L ]'))
            first.append(i)

        # Reactions based on page post type
        third = []
        for x in list2:
            s = "SELECT SUM(likes),SUM(love),SUM(haha),SUM(wow),SUM(sad),SUM(angry),sum(shares),sum(comments) FROM " + tablename + " where typ=%s" % (
            x)
            cur.execute(s)
            paget = list(cur.fetchall())

            j = int(sum(paget[0]))
            third.append(j)

            # Overall Reactions on page posts
            s = "SELECT SUM(likes),SUM(love),SUM(haha),SUM(wow),SUM(sad),SUM(angry),sum(shares),sum(comments) FROM " + tablename
            cur.execute(s)
            paget = list(cur.fetchall())

        # Reactions from page postings

        x = 0
        lks = []
        lov = []
        hah = []
        wo = []
        sa = []
        an = []
        sh = []
        com = []
        tarikh = []

        days_to_subtract = daydiff
        dat1 = datetime.today() - timedelta(days=days_to_subtract)
        days=daydiff



        while days >= 0:
            temp = str(dat1)
            temp = str(temp[0:10].translate(None, "-"))
            temp = int(temp)

            s = "SELECT SUM(likes)FROM " + tablename + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            ke = list(cur.fetchall())
            lks.append(ke[0][0])

            s = "SELECT SUM(love)FROM " + tablename + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            lov.append(lo[0][0])

            s = "SELECT SUM(haha)FROM " + tablename + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            hah.append(lo[0][0])

            s = "SELECT SUM(wow)FROM " + tablename + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            wo.append(lo[0][0])

            s = "SELECT SUM(sad)FROM " + tablename + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            sa.append(lo[0][0])

            s = "SELECT SUM(angry)FROM " + tablename + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            an.append(lo[0][0])

            s = "SELECT SUM(shares)FROM " + tablename + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            sh.append(lo[0][0])

            s = "SELECT SUM(comments)FROM " + tablename + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            com.append(lo[0][0])
            z=temp
            tarikh.append(str(z))
            dat1 = dat1 + timedelta(days=1)
            days -= 1


        tarikh2 = []
        for x in tarikh:
            y = y = x[0:4] + '/' + x[4:6] + "/" + x[6:]
            tarikh2.append(y)
        for x in range(len(lks)):
            if lks[x] == None:
                lks[x] = 0

        for x in range(len(lov)):
            if lov[x] == None:
                lov[x] = 0

        for x in range(len(hah)):
            if hah[x] == None:
                hah[x] = 0

        for x in range(len(wo)):
            if wo[x] == None:
                wo[x] = 0

        for x in range(len(sa)):
            if sa[x] == None:
                sa[x] = 0

        for x in range(len(an)):
            if an[x] == None:
                an[x] = 0

        for x in range(len(sh)):
            if sh[x] == None:
                sh[x] = 0

        for x in range(len(com)):
            if com[x] == None:
                com[x] = 0


        pageposts=[]
        ndates=[]

        days_to_subtract = daydiff
        dat1 = datetime.today() - timedelta(days=days_to_subtract)
        days=daydiff




        while days >= 0:

            temp = str(dat1)
            temp = str(temp[0:10].translate(None, "-"))
            temp = int(temp)

            s = "SELECT COUNT(*)FROM " + tablename + " where created_time = %d" % temp
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            pageposts.append(lo[0][0])

            z = temp
            ndates.append(str(z))
            dat1 = dat1 + timedelta(days=1)
            days -= 1

        ndates2 = []
        for x in tarikh2:
            y = x[0:4] + '/' + x[4:6] + "/" + x[6:]
            ndates2.append(y)

            # Fan Count
            fandates = []
            fancountry = []
            fannum = []
            table3 = tablename + "fans"

            s = "SELECT DISTINCT time FROM " + table3 + " ORDER BY time ASC"
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            for x in lo:
                s = int(x[0])
                fandates.append(s)

            s = "SELECT DISTINCT country FROM " + table3 + " ORDER BY country ASC"
            cur = myConnection.cursor()
            cur.execute(s)
            lo = list(cur.fetchall())
            for y in lo:
                x = str(y[0])
                x = x.translate(None, "')(, ")
                fancountry.append(x)

            brave = {}
            for x in fancountry:
                s = "SELECT  fancount FROM " + table3 + " where country = '%s' " % x
                cur = myConnection.cursor()
                cur.execute(s)
                lo = list(cur.fetchall())
                for xy in lo:
                    ov = str(xy)
                    uv = int(ov.translate(None, "(,)"))
                    fannum.append(uv)
                brave[x] = fannum
                fannum = []

            print brave

            fandates2 = []
            for x in fandates:
                x = str(x)
                y = x[0:4] + '/' + x[4:6] + "/" + x[6:]
                fandates2.append(y)

            print fandates2

            braver = dict(data=[],
                          layout=dict(title="Fans by Country", xaxis=dict(title='Day'), yaxis=dict(title='Reactions')))

            for key in brave:
                rt = dict(x=fandates2, y=brave[key], type='Scatter', name=key, line=dict(width=2, ))
                braver["data"].append(rt)
            print  braver




        graphs = [
            dict(data=[dict(labels=label1, values=list1, type='pie')], layout=dict(title="Total Page Posts")),
            dict(data=[dict(labels=list2, values=first, type='pie', ),],
                 layout=dict(title="Page Posts Distribution"),  ),

            dict(data=[dict(x=list2, y=third, type='bar', name='PagePosts'),
                       ],
                 layout=dict(title="Reactions")),

            dict(data=[
                dict(x=['likes', 'love', 'haha', 'wow', 'sad', 'angry', 'shares', 'comments'], y=paget[0], type='bar',
                     name='ForPagePosts'),
                ],
                 layout=dict(title="Reactions Distribution",)),

            dict(data=[
                dict(x=tarikh2, y=pageposts, type='Scatter', name='No. of page pageposts', mode='markers',
                     marker=dict(size=10, color='rgba(100, 0, 0, .8)', line=dict(width=1, color='rgb(0, 0, 0)'))),
               ],
                layout=dict(title="No. of Posts", yaxis=dict(zeroline=True), xaxis=dict(zeroline=True))),

            dict(data=[
                dict(x=tarikh2, y=lks, type='Scatter', name='likes', line=dict(color=('rgb(255, 0, 0)'), width=2, )),
                dict(x=tarikh2, y=lov, type='Scatter', name="loves", line=dict(color=('rgb(0, 255, 255)'), width=2, )),
                dict(x=tarikh2, y=hah, type='Scatter', name="haha", line=dict(color=('rgb(205, 12, 24)'), width=2, )),
                dict(x=tarikh2, y=wo, type='Scatter', name="wow", line=dict(color=('rgb(22, 96, 167)'), width=2, )),
                dict(x=tarikh2, y=sa, type='Scatter', name="sad", line=dict(color=('rgb(0, 0, 255)'), width=2, )),
                dict(x=tarikh2, y=an, type='Scatter', name="angry", line=dict(color=('rgb(0, 255, 255)'), width=2, )),
                dict(x=tarikh2, y=sh, type='Scatter', name="shares", line=dict(color=('rgb(255, 255, 0)'), width=2, )),
                dict(x=tarikh2, y=com, type='Scatter', name="comments",
                     line=dict(color=('rgb(255, 0, 255)'), width=2, )), ],
                 layout=dict(title="Reactions over time from page posts", xaxis=dict(title='days'),
                             yaxis=dict(title='Reactions'))),



        ]
        graphs.append(braver)

        ids = ['graph-{}'.format(i) for i, _ in enumerate(graphs)]
        graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)

        s = "Drop table " + tablename
        cur.execute(s)
        myConnection.commit()
        #return HTML page containing graphs
        return render_template('graph.html',
                               ids=ids,
                               graphJSON=graphJSON)

# as soon as user clicks analyze button below function getts triggered
@app.route('/process',methods=['POST'])
def process():
    global page_id
    global tablename
    global flag
    global cur
    global access_token
    global tablename

    #fetch page id from HTML input page
    page_id = str(request.form['pageid'])
    days=int(request.form['days'])
    tablename = page_id.translate(None, '[,(). ]')
    table2=tablename+"visitor"
    fantable=tablename+"fans"

    #create table to store the page data
    s = "CREATE TABLE "+tablename+"(id char(255),link TEXT,typ CHAR(255),category TEXT,message TEXT,story TEXT,created_time INT,shares INT ,comments INT ,likes INT,love INT ,haha INT ,wow INT ,sad INT ,angry INT,emotion TEXT )"

    try:
        cur.execute(s)

        myConnection.commit()
    except:
        flag = 1
    #create table to store the countrywise fan data
    s = "CREATE TABLE "+fantable+"(time INT,country CHAR(255),fancount INT )"

    try:
        cur.execute(s)

        myConnection.commit()
    except:
        flag = 1

    #create table to store the visitor's post data
    s = "CREATE TABLE "+table2+"(id char(255),link TEXT,typ CHAR(255),category TEXT,message TEXT,story TEXT,created_time INT,shares INT ,comments INT ,likes INT,love INT ,haha INT ,wow INT ,sad INT ,angry INT,emotion TEXT )"

    try:
        cur.execute(s)

        myConnection.commit()
    except:
        flag = 1

    #retrieve data frames containing page data,visitor's data & fan following data
    df1 = GetCompletePageData(page_id, access_token,days)
    df2 = taggedpost(page_id, access_token,days)
    df3=fandata(page_id,access_token,days)

    #Store this data to database tables
    store_pageposts(df1)
    store_visitorposts(df2)
    store_fancount(df3)
    print "Data is getting stored"
    return graph(days)

#homepage of tool
@app.route('/')
def home():
    return render_template("home.html")

if __name__ == '__main__':
    app.run()
