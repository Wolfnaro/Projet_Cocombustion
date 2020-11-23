# -*- coding: utf-8 -*-
"""
Created on Tue Oct  6 08:35:07 2020

@author: genaro.soriano
"""

"""
MODEL 3

Faudra remplir dans un txt les valeurs : 
    - Prix d'achat chaque materiau
    - Prix de vente chaque materiau
"""
from gurobipy import *
import numpy as np

###########################################################################
# Definition des constantes
###########################################################################
# Chaque donnée d'entre vient avec les unites comme des constantes. On peut
# definir ces unitées ici en bas selon les unites qu'on veut à la fin. Par
# exemple, si on veut exprimer les résultat en kiloton on met ton = 0.001. 
# Si on veut rester dans l'unité ton on met ton = 1.
###########################################################################
# Unites (Il faut changer que ton selon l'unité qu'on veux avoir)
ton = 0.001                                     # On va afficher tout en Kton
kt = 1000 * ton                                 # kton

euro = 1/1000000                               # Millions
k_euro = 1000 * euro

megajoule = 1/3600                              # MWh (facteur pour passer de joules a MWh)
terajoule = 1000000 * megajoule                    # MWh
###########################################################################

puissance_nominale = 250                        # MW    Pourquoi 250 ???????
prod_moyenne = 7500                             # Heures
efficacite = 0.38
annee_debut = 2016 # Je n'ai pas encorporé celle-ci. Il faudra l'ajouter après
porcentage_carbon = 0.1                         # Ratio entre Carbon et Biomasse

duplic_capacite = False                  # €
cout_duplic_capacite = 500000*euro                  # €
capacite_jour = 1500 * ton                      # t/jour

dispositif_sechage = False                       # True si on va utliser le dispositive de sechage
quantite_dispositives_sechage = 1
instalation_sechage = 600000*euro              # €
capacite_sechage = 150*kt                       # kt/an

energ_prod = puissance_nominale * prod_moyenne  # MWh
energ_brut = energ_prod / efficacite            # MWh
horizon = 20

cout_incorp_0 = 215 * euro/terajoule
cout_incorp_1 = 430 * euro/terajoule


# p_achat (euro/ton), humidite, dispo (kt)
combustibles, p_achat,          humid,  humid_sech, dispo = multidict({
        'carb': [100*euro/ton,   0,     0,       GRB.INFINITY],
        'biog': [190*euro/ton,   0,     0,       700*kt],       #Granulé # on n'a pas consideré le 5% d'humidité avant broyage 
        'vert': [25*euro/ton,    0.4,   0.05,    52*kt],
        'bois': [0*euro/ton,     0.2,   0.05,    GRB.INFINITY],
        'recy': [12*euro/ton,    0.05,  0.05 ,   85*kt]
    })

# p_achat (euro/t), dispo 1 (kt), dispo 2 (kt), GES (kg), route (km)
bois_prove, p_achat_bois, dispo_bois_debut, dispo_bois_final, ges_bois, route_bois = multidict({
'30A':	[128*euro/ton,   18*kt,  21*kt,	  0.04,	 230],
'30C':	[120*euro/ton,   21*kt,  43*kt,	  0.03,	 210],
'48':	[128*euro/ton,   12*kt,  75*kt,	  0.04,	 230],
'07':	[116*euro/ton,   8*kt,   56*kt,	  0.03,	 200],
'13':	[44*euro/ton,	 47*kt,  51*kt,   0.00,	 20],
'84':	[76*euro/ton,	 24*kt,  28*kt,   0.02,	 100],
'83':	[60*euro/ton,	 27*kt,  27*kt,   0.01,	 60],
'05':	[100*euro/ton,   15*kt,  21*kt,	  0.03,	 160],
'04':	[88*euro/ton,	 26*kt,  37*kt,   0.02,	 130],
'200':	[116*euro/ton,   27*kt,  27*kt,	  0.03,	 200],
'300':	[156*euro/ton,   56*kt,  56*kt,	  0.05,	 300],
'400':	[196*euro/ton,   93*kt,  93*kt,	  0.07,	 400]
})

###########################################################################
# Données pas encore utilisée
###########################################################################

cout_invertissement = 1.2*euro/ton       # par ton de granulés 

# dispo_vert (kt), p_achat_vert (euro/ton), route_vert(km), 
residus_vert, dispo_vert, p_achat_vert, route_vert, morceau = multidict({
        'vert1': [1*kt,    4*euro/ton,    10,   1],
        'vert2': [7*kt,    7*euro/ton,    20,   1],
        'vert3': [22*kt,   10*euro/ton,   30,   1],
        'vert4': [29*kt,   16*euro/ton,   50,   1],
        'vert5': [52*kt,   25*euro/ton,   80,   1],
        'vert6': [57*kt,   31*euro/ton,   100,  1],
        'vert7': [53*kt,   46*euro/ton,   150,  1],
        'vert8': [210*kt,  61*euro/ton,   200,  1],
        'vert9': [313*kt,  76*euro/ton,   250,  1],
    })

###########################################################################
# Fonctions auxiliaires
###########################################################################
#GJ/t
def pci_from_humidity(humidity):
    return 18 - 21 * humidity                   #Pour le torrifie soit on a 5% soit on a 18Gj après sechage. Mais après sechage toute la biomasse aura 5% >>> contradiction ?

# PCI en MWh/ton
def pci(combustible,sechage):
    if(sechage == False): valeur_hum = humid[combustible]
    else: valeur_hum = humid_sech[combustible]
    
    pcigj = 25 if combustible=='carb' else pci_from_humidity(valeur_hum)
    return pcigj/(3.6 * ton)

# prix unitaire en euro/MWh
def p_vente(combustible,n):
    t=0
#    t=0.02
    return 43*euro*(1+t)**n if combustible=='carb' else 115*euro*(1+t)**n
#    return 43*euro if combustible=='carb' else 115*euro

# dispo en kton
def dispo_bois(prove, annee):
    return dispo_bois_debut[prove] if annee <= 10 else dispo_bois_final[prove]

def coefficient(matiere, sechage):
    return (100-humid['biog'])/95 if sechage == True else 1.0 

###########################################################################
# Modelisation 
###########################################################################

model = Model('TP OSE Octobre 2019')
model.modelSense = GRB.MAXIMIZE
    
###########################################################################
# Definition des variables 
###########################################################################

# masses en ktons
MASSE = {}                                               # index combustible, annee
MASSE_BOIS_PROVE = {}                                    # index provenance, annee

MASSE_HUMID = {}                                    # Index combustible_sech-humid, année  >>> MASSE
MASSE_A_SECHER ={}
MASSE_SECHE = {}                 # Masse seché!!!

# Variables booléens 
INCORPORATION_BIOMASSE = {}

matiere_humid = ['vert', 'biog']
pas_besoin_secher = ['carb', 'bois', 'recy']

for i in range(horizon):
    for c in combustibles:
        MASSE[c,i] = model.addVar(lb = 0, vtype = GRB.CONTINUOUS, ub = dispo[c], name=f'm{c}{i}')
        
    for s in matiere_humid:
        MASSE_HUMID[s,i] = model.addVar(lb = 0, vtype = GRB.CONTINUOUS, name=f'masse_humid{s}{i}')
        MASSE_A_SECHER[s,i] = model.addVar(lb = 0, vtype = GRB.CONTINUOUS, name=f'masse_a_secher{s}{i}')
                
    for p in bois_prove:
        MASSE_BOIS_PROVE[p,i] = model.addVar(lb = 0, ub = dispo_bois(p, i), vtype = GRB.CONTINUOUS, name=f'mb{p}{i}')

    INCORPORATION_BIOMASSE[i] = model.addVar(vtype = GRB.BINARY, name=f'incorp_biomasse{i}')

###########################################################################
# Definition des relations et contraintes 
###########################################################################

benef = []
for i in range(horizon):
    if dispositif_sechage :
        benef.append(quicksum((p_vente(c,i) * pci(c,False) * efficacite - p_achat[c]) * MASSE[c,i] for c in pas_besoin_secher)
                     + quicksum(coefficient(c,False) * MASSE_HUMID[c,i] * pci(c,False) * efficacite * p_vente(c,i) for c in matiere_humid)                       # (vent humid total)
                     + quicksum(coefficient(c,True) * MASSE_A_SECHER[c,i] * (pci(c,True)  * efficacite * p_vente(c,i)) for c in matiere_humid)    # (vent du seché)
                     - quicksum(MASSE[c,i] * p_achat[c] for c in matiere_humid)                                                   # (achat total)
                     - quicksum(p_achat_bois[p]*MASSE_BOIS_PROVE[p,i] for p in bois_prove) 
                     - (cout_incorp_0 * (1 - INCORPORATION_BIOMASSE[i]) + cout_incorp_1 * INCORPORATION_BIOMASSE[i]) * energ_prod)            #c'est bien energie prod? ou plutot energie biomasse efficace ?
    else:
        benef.append(quicksum((p_vente(c,i) * pci(c,False) * efficacite - p_achat[c]) * MASSE[c,i] for c in combustibles)
                     - quicksum(p_achat_bois[p]*MASSE_BOIS_PROVE[p,i] for p in bois_prove)
                     - (cout_incorp_0 * (1 - INCORPORATION_BIOMASSE[i]) + cout_incorp_1 * INCORPORATION_BIOMASSE[i]) * energ_prod)            #c'est bien energie prod? ou plutot energie biomasse efficace ?

objective = quicksum(benef[i] for i in range(horizon)) - dispositif_sechage * quantite_dispositives_sechage * instalation_sechage - duplic_capacite * cout_duplic_capacite
    
model.setObjective(objective)

CONTR_CARB  = []     # 0.9m_c(t) - 0.1 * SUM_1(m_i(t)) >= 0
CONTR_PROD  = []     # (m_c(t) * PCI_c + SUM_1(m_i(t) * PCI_i)) = Energie Brute = Energie Produit / efficacite
CONTR_STOCK = []     # m_b + m_v + m_r <= 1500 * 365
CONTR_BOIS  = []     # m_b = SUM_2(m_bj(t))
CONTR_COUT_INCORPO = []
CONTR_A_SECHER  = []     # masse = masse_a_sech + masse_humid 

masse_max_charbon = energ_brut / pci('carb',False)

for i in range(horizon):
    biomasse = quicksum(MASSE[c,i] for c in combustibles if c != 'carb')
    CONTR_CARB.append(model.addConstr((1 - porcentage_carbon) * MASSE['carb', i] >= porcentage_carbon * biomasse))
    if dispositif_sechage:
        CONTR_PROD.append(model.addConstr(quicksum(MASSE[c, i] * pci(c,False) for c in pas_besoin_secher) + 
                                          quicksum(pci(c,False) * MASSE_HUMID[c, i] + 
                                                   MASSE_A_SECHER[c, i] * coefficient(c, True) * pci(c, True) for c in matiere_humid) == energ_brut))
        CONTR_A_SECHER.append(model.addConstr(quicksum(MASSE_A_SECHER[p,i] for p in matiere_humid) <= 150*kt))
        for j in matiere_humid:
            CONTR_A_SECHER.append(model.addConstr(MASSE[j,i] == MASSE_HUMID[j,i] + MASSE_A_SECHER[j,i]))
    else:
        CONTR_PROD.append(model.addConstr(quicksum(MASSE[c, i] * pci(c,False) for c in combustibles) == energ_brut))
    biomasse_brute = quicksum(MASSE[c,i] for c in ['vert', 'recy', 'bois'])
    CONTR_STOCK.append(model.addConstr(biomasse_brute <= 365 * capacite_jour * (1 + duplic_capacite) ))
    CONTR_BOIS.append(model.addConstr(MASSE['bois', i] ==  quicksum(MASSE_BOIS_PROVE[p,i] for p in bois_prove)))
    CONTR_COUT_INCORPO.append(model.addConstr(biomasse >= MASSE['carb', i] - masse_max_charbon * (1 - INCORPORATION_BIOMASSE[i])))

model.write('new.lp')
model.optimize()
assert model.status == GRB.status.OPTIMAL, f"solver stopped with status {M.status}"

###### Affichage des résultats
for i in (0, horizon-1):
    print(f"masse de combustibles à année {i+1} est :")
    for c in combustibles:
        print(f"{c}: {MASSE[c,i].x:.1f}")
    print(f"profit pour année {i+1} = {benef[i].getValue():.2f}")
    ratio = MASSE['carb',i].x / sum(MASSE[c,i].x for c in combustibles)
    print(f"ratio charbon/masse totale à année {i+1} est : {ratio*100:.0f} %")
    
# # Calcul du coefficient des Masses, ceci afin de sav
#     for c in combustibles:
#         coef_combustible = pci(c)*efficacite*p_vente(c) - p_achat[c] 
#         print(f"{c}: {coef_combustible:.1f}")
    
# # 
#     for b in bois_prove:
#         coef_combustible = pci('bois')*efficacite*p_vente(b) - p_achat_bois[b] 
#         print(f"{b}: {coef_combustible:.1f}")
        
        

####### Bloc de notes 
#
# Avant incorporation du sechage
# ===========================
# deux matière avec humidité : bois et le vert
# bois : 12 fournisseurs
#
#
# Après incorporation du sechage
# ===========================
#
#
