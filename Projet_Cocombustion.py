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
###########################################################################
# Cette version et la suivante de la corrigé par la profe sauf qu'on a corrigé
# les problèmes de unites et on a ajouté la hipotese H8
# Si on ajoute cette hipotese on obtient 0 de vert. On peut dire qu'il est
# moins priorité que quelques recy (Regarder les deux lignes CONTR_SECH)
# Aussi ici on a fait avec puissance_nominale = 250, tant que la prof a changé
# par 150
#
# Hemos agregado el costo de incorporacion. Las lineas que intervienen son 
# la ultima linea de la utilidad, la linea de definicion de la contrante de 
# de incorporacion y la linea de la contrainte.
#
# Consejo : intentar hacer el calculo unicamente con carbono y ver cuanto deberia salir
# segun el sujet habia una ganancia que miles de euros y no en millards (quizas es exagerado el monto)
# revisa cuanto sale solo tomando carbono.
###########################################################################
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
instalation_sechage = 0*euro                   # €
duplic_capacite = 500000*euro                  # €
capacite_jour = 1500 * ton                      # t/jour
instalation_sechage = 600000*euro              # €
capacite_sechage = 150*kt                       # kt/an
energ_prod = puissance_nominale * prod_moyenne  # MWh
energ_brut = energ_prod / efficacite            # MWh
horizon = 20

cout_incorp_0 = 215 * euro/terajoule
cout_incorp_1 = 430 * euro/terajoule

dispositif_sechage = True                       # True si on va utliser le dispositive de sechage

# p_achat (euro/ton), humidite, dispo (kt)
combustibles, p_achat, humid, dispo = multidict({
        'carb': [100*euro/ton,   0,      GRB.INFINITY],
        'biog': [190*euro/ton,   0,      700*kt],
        'vert': [25*euro/ton,    0.4,    52*kt],
        'bois': [0*euro/ton,     0.2,    GRB.INFINITY],
        'recy': [12*euro/ton,    0.05,   85*kt]
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

# p_achat_granule (euro/ton), cout_fixe_granule(k_euro), dispo(kt/an), mer(km), route_granule(km)
# granule, p_achat_granule, cout_fixe_granule, dispo, mer, route_granule = multidict({
#         'Caroline-du-Sud':  [190*euro/ton,   100*k_euro,      700*kt,   7000,   250],
#         'Brasil':           [170*euro/ton,   120*k_euro,      600*kt,   8500,   1000],
#         'Quebec':           [180*euro/ton,   110*k_euro,      450*kt,   5000,   500],
#         'Canada_Pacifique': [250*euro/ton,   100*k_euro,      1000*kt,  16500,  800],
#         'Portugal':         [240*euro/ton,   5*k_euro,        350*kt,   0,      1700]
#         'Russie':           [300*euro/ton,   6*k_euro,        600*kt,   0,      3000]
#     })




###########################################################################
# Fonctions auxiliaires
###########################################################################
#GJ/t
def pci_from_humidity(humidity):
    return 18 - 21 * humidity

# PCI en MWh/ton
def pci(combustible):
    pcigj = 25 if combustible=='carb' else pci_from_humidity(humid[combustible])
    return pcigj/(3.6 * ton)

# prix unitaire en euro/MWh
def p_vente(combustible):
    return 43*euro if combustible=='carb' else 115*euro

# dispo en kton
def dispo_bois(prove, annee):
    return dispo_bois_debut[prove] if annee <= 10 else dispo_bois_final[prove]

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
# Variables booléens 
INCORPORATION_BIOMASSE = {}

for i in range(horizon):
    for c in combustibles:
        MASSE[c,i] = model.addVar(lb = 0, vtype = GRB.CONTINUOUS, ub = dispo[c], name=f'm{c}{i}')
    for p in bois_prove:
        MASSE_BOIS_PROVE[p,i] = model.addVar(lb = 0, ub = dispo_bois(p, i), vtype = GRB.CONTINUOUS, name=f'mb{p}{i}')
    INCORPORATION_BIOMASSE[i] = model.addVar(vtype = GRB.BINARY, name=f'incorp_biomasse{i}')

###########################################################################
# Definition des relations et contraintes 
###########################################################################

utilite = []
for i in range(horizon):
    utilite.append(quicksum((p_vente(c) * pci(c) * efficacite - p_achat[c]) * MASSE[c,i] for c in combustibles)
                   - quicksum(p_achat_bois[p]*MASSE_BOIS_PROVE[p,i] for p in bois_prove)
                   - (cout_incorp_0 * (1 - INCORPORATION_BIOMASSE[i]) + cout_incorp_1 * INCORPORATION_BIOMASSE[i]) * energ_prod)            #c'est bien energie prod? ou plutot energie biomasse efficace ?

objective = quicksum(utilite[i] for i in range(horizon)) - instalation_sechage - duplic_capacite
    
model.setObjective(objective)

# Pour les commentaires dans les contraintes : 
#    - SUM_1 est la fonction somme dans tous les index i qui appartient à l'intervale I = {bois, vert, recy, torr}
#    - SUM_2 est la fonction somme dans tous les index j qui appartient à l'intervale I = {1, 2, ..., 12}

CONTR_CARB  = []     # 0.9m_c(t) - 0.1 * SUM_1(m_i(t)) >= 0
CONTR_PROD  = []     # (m_c(t) * PCI_c + SUM_1(m_i(t) * PCI_i)) = Energie Brute = Energie Produit / efficacite
CONTR_STOCK = []     # m_b + m_v + m_r <= 1500 * 365
CONTR_BOIS  = []     # m_b = SUM_2(m_bj(t))
#CONTR_SECH  = []     # Capacité maximale de séchage : 150 kt (H8)
CONTR_COUT_INCORPO = []

masse_max_charbon = energ_brut / pci('carb')

for i in range(horizon):
    biomasse = quicksum(MASSE[c,i] for c in combustibles if c != 'carb')
    CONTR_CARB.append(model.addConstr((1 - porcentage_carbon) * MASSE['carb', i] >= porcentage_carbon * biomasse))
    CONTR_PROD.append(model.addConstr(quicksum(MASSE[c, i] * pci(c) for c in combustibles) == energ_brut))
    biomasse_brute = quicksum(MASSE[c,i] for c in ['vert', 'recy', 'bois'])
    CONTR_STOCK.append(model.addConstr(biomasse_brute <= 365 * capacite_jour))
    CONTR_BOIS.append(model.addConstr(MASSE['bois', i] ==  quicksum(MASSE_BOIS_PROVE[p,i] for p in bois_prove)))
#    CONTR_SECH.append(model.addConstr(biomasse_brute <= capacite_sechage))
    CONTR_COUT_INCORPO.append(model.addConstr(biomasse >= MASSE['carb', i] - masse_max_charbon * (1 - INCORPORATION_BIOMASSE[i])))
model.write('new.lp')
model.optimize()
assert model.status == GRB.status.OPTIMAL, f"solver stopped with status {M.status}"

###### Affichage des résultats
for i in (0, horizon-1):
    print(f"masse de combustibles à année {i+1} est :")
    for c in combustibles:
        print(f"{c}: {MASSE[c,i].x:.1f}")
    print(f"profit pour année {i+1} = {utilite[i].getValue():.2f}")
    ratio = MASSE['carb',i].x / sum(MASSE[c,i].x for c in combustibles)
    print(f"ratio charbon/masse totale à année {i+1} est : {ratio*100:.0f} %")
    
# Calcul du coefficient des Masses, ceci afin de sav
    for c in combustibles:
        coef_combustible = pci(c)*efficacite*p_vente(c) - p_achat[c] 
        print(f"{c}: {coef_combustible.x:.1f}")
    
# 
    for b in bois_prove:
        coef_combustible = pci(b)*efficacite*p_vente(b) - p_achat_bois[b] 
        print(f"{b}: {coef_combustible.x:.1f}")
        
        


