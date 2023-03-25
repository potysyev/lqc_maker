import json
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from welly import Well, Project, Curve
import matplotlib.pyplot as plt
import os
import tkinter as tk
from tkinter import filedialog

def imports_dicts():

    with open('famdict.json', 'r', encoding='utf-8') as f:
        famdict = json.load(f)
    with open('lqcdict.json', 'r', encoding='utf-8') as f:
        lqcdict = json.load(f)

    return famdict, lqcdict
#%%
def cname_to_lqcname(cname, lqcdict):
    lqcname = ''
    if any(cname in sublist for sublist in list(lqcdict.values())):  # есть ли кривая в словаре lqcdict гделибо
        lqcname = list(lqcdict.keys())[list(lqcdict.values()).index(
            [sublist for sublist in list(lqcdict.values()) if cname in sublist][0])]  # выбираем из словаря ключ соотвествующий найденному в значениях имени кривой
    return lqcname
#%%

#%%
def make_las_project(las_path):
    las_list = []
    for root, dirs, files in os.walk(las_path):
        for file in files:
            if file.lower().endswith(".las"):
                las_list.append(os.path.join(root, file))

    las_project = Project.from_las(las_list, index='M')

    return las_project
#%%
def make_intevals(las_project, classification_distance=300):
    dataset_list = {}
    for ind, w in enumerate(las_project):

        well_name = str(w.name).replace(" ", "")
        ds_start = w.header[w.header['mnemonic'] == 'STRT']['value'].values[0]
        ds_stop = w.header[w.header['mnemonic'] == 'STOP']['value'].values[0]
        if ds_start > ds_stop:
            ds_start, ds_stop = ds_stop, ds_start

        if well_name == 'WELL' or well_name == '':
            well_name = str(w.fname)
            print("!!! file {} does not contain well name. Using file name instead".format(w.fname)) #задавать вручную

        if well_name not in dataset_list.keys() :
            dataset_list[well_name] = []

        dataset_list[well_name].append([well_name, ind, ds_start, ds_stop, ds_stop - ds_start])


    for well_name in dataset_list.keys():
        ds_df = pd.DataFrame(dataset_list[well_name], columns=['well_name', 'project_index', 'top', 'bottom', 'size'])
        ds_df.sort_values(by=['top', 'size'], inplace=True)
        dbs = DBSCAN(eps=classification_distance, min_samples=1).fit(ds_df[['top', 'bottom']])
        ds_df['labels'] = dbs.labels_
        ds_df = ds_df.drop('size', axis=1)
        #dataset_list_out[well_name] = ds_df.to_dict('split')['data']

    #print(dataset_list_out)
    return ds_df
#%%
def make_table(lasproject, dataset_list, lqcdict):
    columns =['Well Name']
    # Create a new workbook and worksheet for the output

    for i, log in enumerate(lqcdict.keys()):
        columns.append(log)
    columns.append('Other Logs')
    logsdata = pd.DataFrame(columns=columns)

    # Write the header row
    for  i, well in enumerate(lasproject):
        #print(well)
        # Get the well name
        well_name = well.name
        ds_label=dataset_list.loc[dataset_list['project_index']==i]['labels'].values[0]


        if well_name not in logsdata['Well Name'].values:
            logsdata = logsdata.append(pd.Series(name=well_name))
            logsdata.loc[well_name, 'Well Name'] = well_name

        logsdata.fillna('', inplace=True)


        # Loop through all the logs in the well object
        for log_name in well.data.keys():

            #start and stop depth of the log
            w = well.data[log_name]

            start_depth = well.data[log_name].start
            stop_depth = well.data[log_name].stop
            lqcname = cname_to_lqcname(log_name, lqcdict)
            #check if log_name exists in the datafarme columns
            if lqcname!='' and lqcname in logsdata.columns:


                if logsdata.loc[well_name, lqcname].find(':')==-1:
                    logsdata.loc[well_name, lqcname] = "{}: {} - {} \n".format(ds_label,start_depth,stop_depth)
                else:
                    ind = int(logsdata.loc[well_name, lqcname].find(':'))

                    if int(logsdata.loc[well_name, lqcname][0:ind]) < int(ds_label):

                        logsdata.loc[well_name, lqcname] = logsdata.loc[well_name, lqcname] +"{}: {} - {} \n".format(ds_label,start_depth,stop_depth)
                    else:
                        logsdata.loc[well_name, lqcname] = "{}: {} - {} \n".format(ds_label,start_depth,stop_depth) + logsdata.loc[well_name, lqcname]

            else:

                logsdata.loc[well_name, "Other Logs"] = logsdata.loc[well_name, "Other Logs"] + log_name +', '





    # Save the dataframe as xls file
    logsdata.to_excel('logs.xls', index=False)


#

def lqclogdata(wLQC, dataset_ind, dslabel_):
    logs = []
    lqcname = ''
    unitname = ''
    version_index= 0
    for cname in las_project[dataset_ind].data.keys():
        if cname_to_lqcname(cname,lqcdict)!= '':
            lqcname = cname_to_lqcname(cname,lqcdict)  + dslabel_  #выбираем из словаря ключ соотвествующий найденному в значениях имени кривой
            if lqcname in wLQC.data.keys():
                clist = [i for i in wLQC.data.keys() if i.find(lqcname) != -1]
                if len(clist) >= 1:
                    lqcname = lqcname + "_" + str(len(clist))

            if lqcname.find("_") == -1:
                version_index = len(lqcname)
            else:
                version_index = lqcname.find("_")

            if lqcname[0:version_index] in famdict.keys():
                if las_project[dataset_ind].data[cname].units != famdict[lqcname[0:version_index]][1]:

                    if lqcname == "NPHI":  # добавить проверку по конкретным методам ГК НК
                        if las_project[dataset_ind].data[cname].mean().iloc[0] < 1:
                            unitname = "v/v"
                        else:
                            unitname = "%"

                    elif lqcname == "GR":
                        if las_project[dataset_ind].data[cname].mean().iloc[0] < 50:
                            unitname = "uR/H"
                        else:
                            unitname = "Gapi"

                    elif lqcname == "CALI":
                        if las_project[dataset_ind].data[cname].mean().iloc[0] < 1:
                            unitname = "m"
                        else:
                            unitname = "mm"
                    else:
                        unitname = famdict[lqcname[0:version_index]][1]
                else:
                    unitname = las_project[dataset_ind].data[cname].units

                logs.append([cname, lqcname, unitname])


    return logs
#%%
def make_lqc_las(dataset_list, las_project):
    dataset_list.sort_values(by=['well_name', 'labels'], inplace=True)
    print(dataset_list)
    for well in list(dataset_list["well_name"].unique()):

        #determine maximum depth for lqc dataset and create list for dataframe index

        max_depth = dataset_list.loc[dataset_list["well_name"]==well,'bottom'].max()
        min_depth = dataset_list.loc[dataset_list["well_name"]==well,'top'].min()

        #MD = [round(d * 0.1, 1) for d in range(0, int(round((max_depth + 5) / 0.1, 0)) + 1)]

        wLQC = Well()
        wLQC.name = well


        for index, row in dataset_list[dataset_list["well_name"]==well].iterrows():

            dataset_ind = row["project_index"]
            dslabel = row["labels"]

            if dslabel == 0:
                dslabel_ = ""
            else:
                dslabel_ = "_" + str(dslabel)


            #copy curve object correctly to preserve unit information
            #assign or check units for curves
            for cname, lqcname, unitname in lqclogdata(wLQC, dataset_ind, dslabel_):

                wLQC.data[lqcname] = Curve(data=las_project[dataset_ind].data[cname].values, index=las_project[dataset_ind].data[cname].index,mnemonic=lqcname, units=unitname)\
                    .to_basis(start=min_depth-5, stop=max_depth + 5, step=0.1)

        if len(wLQC.data.keys()) > 0:
            wLQC.to_las(well +"_LQC.las")
#%%


if __name__ == "__main__":
    famdict, lqcdict = imports_dicts()

    #las_path, LWD_splice = folder_path_and_splice_state_form()
    las_path = input("Folder path: ")


    las_project = make_las_project(las_path)
    dataset_list = make_intevals(las_project)
    make_table(las_project, dataset_list, lqcdict)


    make_lqc_las(dataset_list, las_project)
    print("Done")