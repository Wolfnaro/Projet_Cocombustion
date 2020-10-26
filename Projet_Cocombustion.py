# -*- coding: utf-8 -*-
"""
Created on Tue Oct  6 08:35:07 2020

@author: genaro.soriano
"""

"""
Info sur la version 
====================

Projet du cocombustion avancé avec les 08 hypothèses avec les considerations suivantes :
    - Vesion juste avant la correction du professeur
    - Puissance nominale = 150 MWh
    - 20 optimisation à 20ans
    - Plusieurs fournisseurs de bois frais 
    - Morceaux residus vert defini
    Test
"""

from gurobipy import *
import numpy as np

###########################################################################
# Fonctions auxiliaires
###########################################################################
def pci_from_humidity(humidity):
    return (18 - 21 * humidity)                                 # GJ/ton

###########################################################################
# Definition des constantes
###########################################################################
megajoule = 1/3600                                                              # MWh (facteur pour passer de joules a MWh)
puissance_nominale = 150                                                        # MW
prod_moyenne = 7500                                                             # Heures
efficacite = 0.38
annee_debut = 2016                                                              # Je n'ai pas encorporé celle-ci. Il faudra l'ajouter après
porcentage_carbon = 0.1                                                         # Ratio entre Carbon et Biomasse
cout_instalation_sechage = 0                                                    # €
duplic_capacite = 500000                                                        # €
capacite_jour = 1500                                                            # t/jour

dispositif_sechage = True                                                       # True si on va utliser le dispositive de sechage

# Humidite des materiaux
humid_biom_brute_vert = 0.40
humid_biom_brute_recy = 0.05
humid_biom_brute_bois = 0.20
if dispositif_sechage : 
    humid_biom_brute_vert = 0.05
    humid_biom_brute_recy = 0.05
    humid_biom_brute_bois = 0.05
    cout_instalation_sechage = 600000                                           # €

# PCI des materiaux
pci_carb = 25 * 1000 * megajoule                                                # MWh/ton
pci_torr = 18 * 1000 * megajoule                                                # MWh/ton
pci_vert = pci_from_humidity(humid_biom_brute_vert) * 1000 * megajoule          # MWh/ton
pci_recy = pci_from_humidity(humid_biom_brute_recy) * 1000 * megajoule          # MWh/ton
pci_bois = pci_from_humidity(humid_biom_brute_bois) * 1000 * megajoule          # MWh/ton

# Prix de vent de carbon et biomasse pour 20 ans
p_vent_carb = [43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43]                       # €/MWh
p_vent_biog = [115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115]   # €/MWh

# Prix d'achat des materiaux
p_achat_carb = 100                                                               # €/ton
p_achat_torr = 190                                                               # €/ton
p_achat_vert = 25                                                                # €/ton
p_achat_recy = 12                                                                # €/ton
p_achat_bois = [128, 120, 128, 116, 44, 76, 60, 100, 88, 116, 156, 196]          # €/ton

# disponibilite des materieux
dispo_torr = 700 * 1000                                                          # ton/an
dispo_vert = 52 * 1000                                                           # ton/an
dispo_recy = 85 * 1000                                                           # ton/an 
# disponibilite des 12 fourniseurs de bois
dispo_bois_debut = [18, 21, 12, 8, 47, 24, 27, 15, 26, 27, 56, 93] * 1000        # ton/an
dispo_bois_final = [21, 43, 75, 56, 51, 28, 27, 21, 37, 27, 56, 93] * 1000       # ton/an

energ_prod = puissance_nominale * prod_moyenne                                          # MWh
energ_brut = energ_prod / efficacite                                                    # MWh

###########################################################################
# Modelisation 
###########################################################################

model = Model('TP OSE Octobre 2019')
model.modelSense = GRB.MAXIMIZE
    
###########################################################################
# Definition des variables 
###########################################################################
MASSE_CARB = []                                                                         # index temp
MASSE_TORR = []                                                                         # index temp
MASSE_VERT = []                                                                         # index temp
MASSE_RECY = []                                                                         # index temp
MASSE_BOIS = []                                                                         # index temp
MASSE_BOIS_PROVE = []                                                                   # index temp
PRIX_ACHAT_TOTAL_BOIS = []                                                              # index temp

for i in range(20):
    MASSE_CARB.append(model.addVar(lb = 0, vtype = GRB.CONTINUOUS))
    MASSE_TORR.append(model.addVar(lb = 0, ub = dispo_torr, vtype = GRB.CONTINUOUS))    
    MASSE_VERT.append(model.addVar(lb = 0, ub = dispo_vert, vtype = GRB.CONTINUOUS))
    MASSE_RECY.append(model.addVar(lb = 0, ub = dispo_recy, vtype = GRB.CONTINUOUS))
    MASSE_BOIS.append(model.addVar(lb = 0, vtype = GRB.CONTINUOUS))
    PRIX_ACHAT_TOTAL_BOIS.append(model.addVar(lb = 0, vtype = GRB.CONTINUOUS))

    MASSE_BOIS_temp = []                                                                # index fournisseur
    for j in range(12):
        if i <= 10 : 
            dispo = dispo_bois_debut[j]
        else : 
            dispo = dispo_bois_final[j]
        MASSE_BOIS_temp.append(model.addVar(lb = 0, ub = dispo, vtype = GRB.CONTINUOUS))
    MASSE_BOIS_PROVE.append(MASSE_BOIS_temp)

###########################################################################
# Definition des relations et contraintes 
###########################################################################

cout_total = []
energie_vendu = []
for i in range(20):
    energie_vendu.append((p_vent_carb[i] * MASSE_CARB[i] * pci_carb + 
                         p_vent_biog[i] * MASSE_TORR[i] * pci_torr + 
                         p_vent_biog[i] * MASSE_VERT[i] * pci_vert + 
                         p_vent_biog[i] * MASSE_RECY[i] * pci_recy + 
                         p_vent_biog[i] * MASSE_BOIS[i] * pci_bois) * efficacite)
    cout_total.append(((MASSE_CARB[i] * p_achat_carb) + 
                      (MASSE_TORR[i] * p_achat_torr) + 
                      (MASSE_VERT[i] * p_achat_vert) + 
                      (MASSE_RECY[i] * p_achat_recy) + 
                      (PRIX_ACHAT_TOTAL_BOIS[i])))

utilite = quicksum(energie_vendu[i] - cout_total[i] for i in range(20)) - cout_instalation_sechage - duplic_capacite
    
model.setObjective(utilite)
model.update()

# Pour les commentaires dans les contraintes : 
#    - SUM_1 est la fonction somme dans tous les index i qui appartient à l'intervale I = {bois, vert, recy, torr}
#    - SUM_2 est la fonction somme dans tous les index j qui appartient à l'intervale I = {1, 2, ..., 12}

CONTR1 = []     # 0.9m_c(t) - 0.1 * SUM_1(m_i(t)) >= 0
CONTR2 = []     # (m_c(t) * PCI_c + SUM_1(m_i(t) * PCI_i)) = Energie Brute = Energie Produit / efficacite
CONTR3 = []     # m_b + m_v + m_r <= 1500 * 365
CONTR4 = []     # m_b = SUM_2(m_bj(t))
CONTR5 = []     # Prix_Achat_total = SUM_2(prix_unite_fournisuer_j(t) * m_bj(t)  )
for i in range(20):
    achat_forniseur = quicksum(MASSE_BOIS_PROVE[i][j] * p_achat_bois[j] for j in range(12))
    
    CONTR1.append(model.addConstr((1 - porcentage_carbon) * MASSE_CARB[i] - porcentage_carbon * (MASSE_TORR[i] + MASSE_VERT[i] + MASSE_RECY[i] + MASSE_BOIS[i]) >= 0))
    CONTR2.append(model.addConstr((MASSE_CARB[i] * pci_carb + 
                                  MASSE_TORR[i] * pci_torr + 
                                  MASSE_VERT[i] * pci_vert + 
                                  MASSE_RECY[i] * pci_recy + 
                                  MASSE_BOIS[i] * pci_bois) == energ_brut))
    CONTR3.append(model.addConstr(MASSE_BOIS[i] + MASSE_VERT[i] + MASSE_RECY[i] <= 365 * capacite_jour))
    CONTR4.append(model.addConstr(MASSE_BOIS[i] - np.sum(MASSE_BOIS_PROVE, axis = 1)[i] == 0))          # Ici la fonction np.sum est pour calculer la somme des tout la masse acheté au differents fournisseurs, cette information et gardé dans l'axes == 1
    CONTR5.append(model.addConstr(PRIX_ACHAT_TOTAL_BOIS[i] - achat_forniseur == 0))

model.optimize()

print(MASSE_CARB[0].x)
print(MASSE_TORR[0].x)
print(MASSE_VERT[0].x)
print(MASSE_RECY[0].x)
print(MASSE_BOIS[0].x)

for i in range(12) :
    print(MASSE_BOIS_PROVE[0][i].x)
