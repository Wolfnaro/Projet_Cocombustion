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
euros = 1/1000000                               # Milliard
###########################################################################

megajoule = 1/3600                              # MWh (facteur pour passer de joules a MWh)
puissance_nominale = 250                        # MW
prod_moyenne = 7500                             # Heures
efficacite = 0.38
annee_debut = 2016 # Je n'ai pas encorporé celle-ci. Il faudra l'ajouter après
porcentage_carbon = 0.1                         # Ratio entre Carbon et Biomasse
instalation_sechage = 0*euros                   # €
duplic_capacite = 500000*euros                  # €
capacite_jour = 1500 * ton                      # t/jour
instalation_sechage = 600000*euros              # €
capacite_sechage = 150*kt                       # kt/an
energ_prod = puissance_nominale * prod_moyenne  # MWh
energ_brut = energ_prod / efficacite            # MWh
horizon = 1

dispositif_sechage = True                       # True si on va utliser le dispositive de sechage

# p_achat (euros/ton), humidite, dispo (kt)
combustibles, p_achat, humid, dispo = multidict({
        'carb': [100*euros/ton,   0,      GRB.INFINITY],
        'biog': [190*euros/ton,   0,      700*kt],
        'vert': [25*euros/ton,    0.4,    52*kt],
        'bois': [0*euros/ton,     0.2,    GRB.INFINITY],
        'recy': [12*euros/ton,    0.05,   85*kt]
    })

# p_achat (euros/t), dispo 1 (kt), dispo 2 (kt), GES (kg), route (km)
bois_prove, p_achat_bois, dispo_bois_debut, dispo_bois_final, ges_bois, route_bois = multidict({
'30A':	[128*euros/ton,   18*kt,  21*kt,	0.04,	230],
'30C':	[120*euros/ton,   21*kt,  43*kt,	0.03,	210],
'48':	[128*euros/ton,   12*kt,  75*kt,	0.04,	230],
'07':	[116*euros/ton,   8*kt,   56*kt,	0.03,	200],
'13':	[44*euros/ton,	  47*kt,  51*kt,	0.00,	20],
'84':	[76*euros/ton,	  24*kt,  28*kt,	0.02,	100],
'83':	[60*euros/ton,	  27*kt,  27*kt,	0.01,	60],
'05':	[100*euros/ton,   15*kt,  21*kt,	0.03,	160],
'04':	[88*euros/ton,	  26*kt,  37*kt,	0.02,	130],
'200':	[116*euros/ton,   27*kt,  27*kt,	0.03,	200],
'300':	[156*euros/ton,   56*kt,  56*kt,	0.05,	300],
'400':	[196*euros/ton,   93*kt,  93*kt,	0.07,	400]
})

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

# prix unitaire en euros/MWh
def p_vente(combustible):
    return 43*euros if combustible=='carb' else 115*euros

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

for i in range(horizon):
    for c in combustibles:
        MASSE[c,i] = model.addVar(lb = 0, vtype = GRB.CONTINUOUS, ub = dispo[c], name=f'm{c}{i}')
    for p in bois_prove:
        MASSE_BOIS_PROVE[p,i] = model.addVar(lb = 0, ub = dispo_bois(p, i), vtype = GRB.CONTINUOUS, name=f'mb{p}{i}')

###########################################################################
# Definition des relations et contraintes 
###########################################################################

utilite = []
for i in range(horizon):
    utilite.append(quicksum((p_vente(c) * pci(c) * efficacite - p_achat[c]) * MASSE[c,i] for c in combustibles)
                   - quicksum(p_achat_bois[p]*MASSE_BOIS_PROVE[p,i] for p in bois_prove))

objective = quicksum(utilite[i] for i in range(horizon)) - instalation_sechage - duplic_capacite
    
model.setObjective(objective)

# Pour les commentaires dans les contraintes : 
#    - SUM_1 est la fonction somme dans tous les index i qui appartient à l'intervale I = {bois, vert, recy, torr}
#    - SUM_2 est la fonction somme dans tous les index j qui appartient à l'intervale I = {1, 2, ..., 12}

CONTR_CARB  = []     # 0.9m_c(t) - 0.1 * SUM_1(m_i(t)) >= 0
CONTR_PROD  = []     # (m_c(t) * PCI_c + SUM_1(m_i(t) * PCI_i)) = Energie Brute = Energie Produit / efficacite
CONTR_STOCK = []     # m_b + m_v + m_r <= 1500 * 365
CONTR_BOIS  = []     # m_b = SUM_2(m_bj(t))
CONTR_SECH  = []     # Capacité maximale de séchage : 150 kt (H8)

for i in range(horizon):
    biomasse = quicksum(MASSE[c,i] for c in combustibles if c != 'carb')
    CONTR_CARB.append(model.addConstr((1 - porcentage_carbon) * MASSE['carb', i] >= porcentage_carbon * biomasse))
    CONTR_PROD.append(model.addConstr(quicksum(MASSE[c, i] * pci(c) for c in combustibles) == energ_brut))
    biomasse_brute = quicksum(MASSE[c,i] for c in ['vert', 'recy', 'bois'])
    CONTR_STOCK.append(model.addConstr(biomasse_brute <= 365 * capacite_jour))
    CONTR_BOIS.append(model.addConstr(MASSE['bois', i] ==  quicksum(MASSE_BOIS_PROVE[p,i] for p in bois_prove)))
    CONTR_SECH.append(model.addConstr(biomasse_brute <= capacite_sechage))

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


