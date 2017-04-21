# ----- CONFIGURE YOUR EDITOR TO USE 4 SPACES PER TAB ----- #
import sys
import settings

sys.path.append(settings.MADIS_PATH)
import madis
from operator import itemgetter

con1 = madis.functions.Connection('articles.db')


def connection():
    con = madis.functions.Connection('articles.db')
    return con


def gen(mylist):
    for i in mylist:
        yield i


def classify(pubid, topn):
    cur = con1.cursor()
    cur.execute("select var('id',?)", (int(pubid),))
    '''
    # extra query ONLY for checking existance of article
    '''
    exists = cur.execute("select summary from articles where id = var('id')")
    flag = 0
    for i in exists:
        flag = 1
        break
    if flag == 0:
        return [("No such article",), ]

    result = cur.execute("select t1.weight,t1.class,t1.subclass,t2.title from "
                         "(select weight,term,class,subclass from classes) as t1,"
                         "(select strsplitv(summary) as term1,title from articles where id = var('id')) as t2 "
                         "where t1.term=t2.term1;")
    dictionary = {}
    for i in result:
        tuple = (str(i[1]), str(i[2]), str(i[3], ))
        if tuple in dictionary:
            dictionary[tuple] += float(i[0])
        else:
            dictionary[tuple] = float(i[0])
    li = []
    for key, value in dictionary.iteritems():
        li.append((str(key[0]), str(key[1]), float(value), str(key[2]),))
    li = sorted(li, key=itemgetter(2), reverse=True)
    li.insert(0, ("Class", "Subclass", "Weight", "Title",))
    return li[0:int(topn) + 1]


def classify_plain_sql(pubid, topn):
    con = connection()
    cur = con.cursor()
    summary = cur.execute("select summary,title from articles where id = ?",
                          [int(pubid)])  # pare iterator sto apotelesma ths sql entolhs
    classes = {}  # dhmiorgw ena dictionary
    for i in summary:  # gia ka8e summary,title apo ta articles me to dwsmeno id
        li = []  # ftiakse mia lista
        textstring = i[0]  # textsrting = summary
        li = textstring.split()  # h lista pernei san stoixeia tis lekseis tou summary
        for j in li:  # gia ka8e leksh
            word = j  # word = leksh
            terms = cur.execute("select class,subclass,weight as total_weight from classes where term = ?",
                                [str(word)])  # vres tis klasseis me auth th leksh
            if (terms != None):  # ean yparxei estw kai mia klassh gia auth th leksh
                for k in terms:  # gia ka8e mia apo tis klasseis
                    # tuple1 //tuple me klassh,ypoklassh,titlo
                    tuple1 = (str(k[0]), str(k[1]), i[1])
                    if (tuple1 in classes):  # ean to tuple einai sto dictionary
                        classes[tuple1] += float(k[2])  # pros8esai to varos sto a8roisma
                    else:
                        classes[tuple1] = float(k[2])  # alliws dhmourghse neo stoixeio tou dictionary kai arxikopoihse me to varos
    tuplesList = []  # lista apo tuples
    for key, value in classes.iteritems():  # gia ka8es eggrafh tou dictionary
        temp1 = key[0]  # klassh
        temp2 = key[1]  # ypoklassh
        temp3 = value  # varos
        temp4 = key[2]  # titlos
        tuplesList.append((temp1, temp2, temp3, temp4))  # eishgage ta antistoixa stoixeia sth lista
    tuples = tuple(tuplesList) # tuples tuplarei th lista
    results = []
    results = sorted(tuples, key=itemgetter(2), reverse=True)  # sortare to apotelesma
    results.insert(0, ("Class", "Subclass", "Weight\'s sum", "Title"))  # pros8ese kai perigrafh tou apotelesmatos thn arxh
    results = results[0:int(topn) + 1]
    return results


def updateweight(class1, subclass, term, weight):
    con = connection()
    cur = con.cursor()
    cur.execute("select var('class',?)", (str(class1),))
    cur.execute("select var('subclass',?)", (str(subclass),))
    cur.execute("select var('term',?)", (str(term),))

    # vres to vatos ths klasshs,ypoklasshs kai orou pou edwse o xrhsths
    result = cur.execute("select weight from classes "
                         "where class = var('class') and subclass = var('subclass') and term = var('term')")
    flag = 0  # elegxei ean yparxei estw kai ena apotelesma
    for i in result:
        flag = 1
        current_weight = i[0]
    if flag == 0:  # den yparxei apotelesma opote epistrefw error
        return [("Error",), ]
    else: # yparxei apotelesma kai...
        new_weight = (float(current_weight) + float(weight)) / 2  # vriskw to meso oro tou trexontos varous kai autou dwsmen apo to xrhsth
        cur.execute("select var('new_weight',?)", (new_weight,))  # gia prostasia apo injection
        cur.execute("update classes set weight = var('new_weight') "
                    "where class = var('class') and subclass = var('subclass') and term = var('term')")
        # con.commit()
        return [("Ok",), ]


def selectTopNauthors(class1, n):
    con = connection()
    cur = con.cursor()
    cur.execute("select var('class',?)", (str(class1),))
    r = cur.execute("select authors_id,count(*) as written from authors_has_articles where articles_id in "
                    "(select distinct article_id from article_has_class where class = var('class')) "
                    "group by authors_id order by written DESC")
    li = []
    for i in r:
        li.append((i[0], i[1]))
    li.insert(0, ("Authors id", "Written"))
    li = li[0:int(n)] # gyrna tous n syggrafeis
    return li


def findSimilarArticles(articleId, n):
    cur = con1.cursor()
    cur.execute("select var('id',?)", (int(articleId),))
    ids = cur.execute("select id from articles")
    similarities_list = []
    id_list = []  # lista me ta id
    # gia k sta id
    for k in ids:
        id_list.append(int(k[0]))
    for i in id_list:
        if i is int(articleId):  # gia na mhn elegxei simmilarity mme ton eauto tou
            continue
        cur.execute("select var('id_2',?)", (i,))
        similarities = cur.execute("select jaccard(j1.jpack1,j2.jpack2),id,title as similarity from"
                                   "(select jgroup(table1.words) as jpack1 from"  # to jgroup sou epistrefei mia lista jason
                                   "(select t1.words as words from "
                                   "(select strsplitv(summary) as words from articles where id = var('id')) as t1  where words not in "
                                   "(select findcommonterms(summary) from articles)) as table1) as j1,"
                                   "(select jgroup(table2.words) as jpack2 from"
                                   "(select t2.words as words from "
                                   "(select strsplitv(summary) as words from articles where id = var('id_2')) as t2  where words not in "
                                   "(select findcommonterms(summary) from articles)) as table2) as j2,articles where id = var('id_2')")
        for j in similarities:
            similarities_list.append((float(j[0]), int(j[1]), str(j[2]),))
    final_list = []
    for i in similarities_list:
        final_list.append((i[0], i[1], i[2],))
    final_list = sorted(similarities_list, key=itemgetter(0), reverse=True)
    final_list.insert(0, ("Similarity", "Id", "Title",))
    return final_list[0:int(n)]







