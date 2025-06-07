import pandas  as pd
import os
#from openpyxl import load_workbook
import re
from datetime import datetime ,timedelta



#pd.options.display.max_rows = 9999 #augmenter le nbr des lignes max
#print(df.iat[8, 12])
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cs.settings")
django.setup()
from myapp.models import Rapport,Forage,Phase,PhaseStandard,Rapport_imported
rap_imported = Rapport_imported.objects.order_by('-id_rapport_imported').first()
print("hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",rap_imported.url.path)
file_path = rap_imported.url.path
df = pd.read_excel(file_path)
#recherche une str dans le rapport ---------------------------------------------------------------------------
def find_cells_starting_with(df, start_str):
    def starts_with(value):
        if pd.isnull(value):
            return False
        return str(value).startswith(str(start_str))
    mask = df.applymap(starts_with)
    return list(zip(*mask.to_numpy().nonzero()))
import re
from datetime import datetime
global date_is_found 
global date_obj
# date_is_found = False
date_obj = None
import re
from datetime import datetime
def find_first_cell_with_date_prefix_or_fallback(df):
    

    pattern = r"^\s*date\s*:\s*.*"
    for i, row in df.iterrows():
        for j, val in row.items():
            if pd.isnull(val):
                continue
            if re.match(pattern, str(val), re.IGNORECASE):
                print(f"First match at ({i}, {j}) → {val}")
                match = re.search(r"\d{2}/\d{2}/\d{4}", str(val))
                if match:
                    date_str = match.group()
                    print("Date extraite :", date_str)
                    try:
                        date_obj = datetime.strptime(date_str, "%m/%d/%Y").date()
                        print("Objet datetime :", date_obj)
                        date_is_found = True
                        return date_obj
                    except ValueError:
                        print("Format de date invalide.")

    # Si aucune date n'est trouvee :
    fallback_value = df.iat[58, 68]
    date_is_found = False
    print("Aucune date trouvée, valeur de repli :", fallback_value)
    try:
        fallback_date = pd.to_datetime(fallback_value).date()
        print("Date de secours convertie :", fallback_date)
        return fallback_date
    except Exception as e:
        print("Erreur de conversion de la date de secours :", e)
        return None


# recherche la date -----------------------------------------------------------------------------------------------
results = find_first_cell_with_date_prefix_or_fallback(df)  
print("results-----------",results)
print("ooooooooooooooooooooooooo extracted info oooooooooooooooooooooooooo")
phase_actuelle=df.iat[8, 12]
print("phase_actuelle",phase_actuelle)
numrap=df.iat[2, 88]
print("numrap",numrap)
cout_actuel=df.iat[56, 87] 
print("cout_actuel",cout_actuel)
coutCumul_actuel=df.iat[57, 87]
print("coutCumul_actuel",coutCumul_actuel)
depth=df.iat[4, 20]  
print("depth",depth)  
zone=df.iat[1, 34]  
print("zone",zone) 
current_operation=df.iat[43, 59]  
print("current_operation",current_operation)  
planned_operation=df.iat[56, 14]
print("planned_operation",planned_operation)
print("ooooooooooooooooooooooooo extracted info oooooooooooooooooooooooooo")

#forage=Forage.objects.get(zone=zone).order_by('dateDebut').last()
forage=Forage.objects.filter(zone=zone).order_by('dateDebut').last()
print("Forage trouvé :", forage)
if forage is None:
    forage=Forage.objects.last()
    print("Forage trouvé :", forage)
    forage.dateFin=results - timedelta(days=1)
    forage.save()
    print("Forage mis à jour :", forage)
    forage = Forage.objects.create(
        zone=zone,
        description="description",
        dateDebut=results,
        dateFin=results + timedelta(days=70),
        dureePrevistionnelle=70,
    )
    forage.save()
    print("Forage créé :", forage)

rap=Rapport.objects.create(
    idForage=forage,
    numRapport=numrap,
    dateActuelle=results,
    nom_phase=phase_actuelle,
    id_rapport_imported=rap_imported
)
rap.save()
print("Rapport créé :", rap)
rapports = Rapport.objects.filter(idForage=forage).order_by('dateActuelle').last()
phase = Phase.objects.filter(idForage=forage).order_by('idPhase').last()
print("phase_last :",phase)
print("rapports :",rapports)
#heloo=False
import re

def normalize(s):
    if s is None:
        return ""
    return re.sub(r"[\"'\s]", "", str(s)).lower()

if rapports is not None and phase is not None:

    if  normalize(rapports.nom_phase) in normalize(phase.idPhaseStandard.nomDePhase):
          print("###################################################################")
          print("normalize(rapports.nom_phase)",normalize(rapports.nom_phase))
          print("phase.idPhaseStandard.nomDePhase",phase.idPhaseStandard.nomDePhase)
          print("on est dans la meme phase et ancien forage")
          phase.delaiActuel=(rap.dateActuelle-phase.dateDebut).days
          phase.coutActuel=cout_actuel
          phase.depthActuel=depth
          phase.coutCumulatifActuel=coutCumul_actuel
          phase.currentOperation=current_operation
          phase.plannedOperation=planned_operation
          phase.save()
          print("updatedphase", phase)
    elif normalize(rapports.nom_phase) not in normalize(phase.idPhaseStandard.nomDePhase):
          print("---------------------------------------------------------------------")
          print("normalize(rapports.nom_phase)",normalize(rapports.nom_phase[0:2]))
          print("phase.idPhaseStandard.nomDePhase",phase.idPhaseStandard.nomDePhase)
          print("on est dans la nouvelle phase et ancien forage")
          phase_std=PhaseStandard.objects.get(nomDePhase__startswith=normalize(rapports.nom_phase[0:2]))
          print("phase_std",phase_std)
          phase = Phase.objects.create(
          idPhaseStandard=phase_std,
          idForage=forage,
          delaiActuel=1,
          depthActuel=depth,
          dateDebut=results,
          coutActuel=cout_actuel,
          coutCumulatifActuel=coutCumul_actuel,
          currentOperation=current_operation,
          plannedOperation=planned_operation  
          )
          print("updatedphase", phase)
          phase.save()
           
    else:
        print("condition faute")
else:
    print("*********************************************************************")
    print("on est dans la nouvelle phase et nouvel forage")
    phase_std=PhaseStandard.objects.get(nomDePhase__startswith=phase_actuelle[0:2])
    phase = Phase.objects.create(
    idPhaseStandard=phase_std,
    idForage=forage,
    delaiActuel=1,
    coutActuel=cout_actuel,
    dateDebut=results,
    depthActuel=depth,
    coutCumulatifActuel=coutCumul_actuel,
    currentOperation=current_operation,
    plannedOperation=planned_operation  
    )
    phase.save()
    print("newphase", phase)


# phase_std=PhaseStandard.objects.get(nomDePhase__startswith=phase_actuelle)
# rapports = Rapport.objects.filter(idForage=forage).order_by('dateActuelle').last()
# print("Rapport trouvé :", rapports)

# phase = Phase.objects.create(
#     idPhaseStandard=phase_std,
#     idRapport=rap,
#     idForage=forage,
#     delaiActuel=12,
#     coutActuel=cout_actuel,
#     coutCumulatifActuel=coutCumul_actuel,
#     currentOperation=current_operation,
#     plannedOperation=planned_operation  
# )
# phase.save()
# if results:
#     first_row, first_col = results[0]
#     first_value = df.iat[first_row, first_col]   
#     print(f"First match at ({first_row}, {first_col}) → {first_value}")
#     match = re.search(r"\d{2}/\d{2}/\d{4}", first_value) # extraction de la date seulement
#     if match:
#        date_str = match.group()
#        print("Date extraite :", date_str)

#     # Convertir le string en objet datetime
#        date_obj = datetime.strptime(date_str, "%m/%d/%Y").date()
#        print("Objet datetime :", date_obj)
#     else:
#        print("Aucune date trouvée.")
# else:
#     print("No matches found.")
# print(results,"eeeeeeee")
# print(first_value,"mmmmmm")
# text = first_value

# fin de recherche date ---------------------------------------------------------------------------------
# recherche data for me -----------------------------------------------------------------------------------------------
# results_phase = find_cells_starting_with(df, "Date:") 
# print("results_phase",results_phase) 
# if results_phase:
#     first_row_phase, first_col_phase = results_phase[0]
#     first_value_phase = df.iat[first_row_phase, first_col_phase]   
#     print(f"First match at ({first_row_phase}, {first_col_phase}) → {first_value_phase}")
# else:
#     print("No matches found.")
# print(results_phase,"0000000000")# get col and row
# print(first_value_phase,"111111111111")# get content of [row,col]
# fin de recherche data for me  ---------------------------------------------------------------------------------
# col and row of extracted data 
