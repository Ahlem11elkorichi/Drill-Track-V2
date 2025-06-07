from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Rapport_imported, Notification, Rapport, User, Forage, Phase, PhaseStandard
from django.utils import timezone
from django.db.models import Max
import pandas as pd
import re
from datetime import datetime, timedelta
import os

def normalize(s):
    """Helper function to normalize strings for comparison"""
    if s is None:
        return ""
    return re.sub(r"[\"'\s]", "", str(s)).lower()

@receiver(post_save, sender=Rapport_imported)
def process_imported_rapport(sender, instance, created, **kwargs):
    """
    Signal handler that automatically processes imported reports and creates notifications.
    This integrates the logic from import.py directly into the signal handler.
    """
    if created:
        try:
            # Process the Excel file and create Rapport, similar to your import.py
            file_path = instance.url.path
            df = pd.read_excel(file_path)
            
            # Extract data from Excel file
            def find_first_cell_with_date_prefix_or_fallback(df):
                pattern = r"^\s*date\s*:\s*.*"
                for i, row in df.iterrows():
                    for j, val in row.items():
                        if pd.isnull(val):
                            continue
                        if re.match(pattern, str(val), re.IGNORECASE):
                            match = re.search(r"\d{2}/\d{2}/\d{4}", str(val))
                            if match:
                                date_str = match.group()
                                try:
                                    return datetime.strptime(date_str, "%m/%d/%Y").date()
                                except ValueError:
                                    pass

                # Si aucune date n'est trouvée :
                try:
                    fallback_value = df.iat[58, 68]
                    return pd.to_datetime(fallback_value).date()
                except Exception:
                    return timezone.now().date()  # Default to today if all else fails
            
            # Extract all the required data from Excel
            date_rapport = find_first_cell_with_date_prefix_or_fallback(df)
            phase_actuelle = df.iat[8, 12]
            numrap = df.iat[2, 88]
            cout_actuel = df.iat[56, 87]
            coutCumul_actuel = df.iat[57, 87]
            depth = df.iat[4, 20]
            zone = df.iat[1, 34]
            current_operation = df.iat[43, 59]
            planned_operation = df.iat[56, 14]
            
            # Find or create Forage
            forage = Forage.objects.filter(zone=zone).order_by('dateDebut').last()
            if forage is None:
                # Handle case when forage doesn't exist
                last_forage = Forage.objects.last()
                if last_forage:
                    last_forage.dateFin = date_rapport - timedelta(days=1)
                    last_forage.save()
                
                forage = Forage.objects.create(
                    zone=zone,
                    description="description",
                    dateDebut=date_rapport,
                    dateFin=date_rapport + timedelta(days=70),
                    dureePrevistionnelle=70,
                )
            
            # Create Rapport
            rapport = Rapport.objects.create(
                idForage=forage,
                numRapport=numrap,
                dateActuelle=date_rapport,
                nom_phase=phase_actuelle,
                id_rapport_imported=instance  # Link to the imported rapport
            )
            
            # Now handle Phase creation/update
            last_rapport = Rapport.objects.filter(idForage=forage).order_by('dateActuelle').last()
            last_phase = Phase.objects.filter(idForage=forage).order_by('idPhase').last()
            
            if last_rapport is not None and last_phase is not None:
                if normalize(last_rapport.nom_phase) in normalize(last_phase.idPhaseStandard.nomDePhase):
                    # Update existing phase
                    last_phase.delaiActuel = (rapport.dateActuelle - last_phase.dateDebut).days
                    last_phase.coutActuel = cout_actuel
                    last_phase.depthActuel = depth
                    last_phase.coutCumulatifActuel = coutCumul_actuel
                    last_phase.currentOperation = current_operation
                    last_phase.plannedOperation = planned_operation
                    last_phase.save()
                else:
                    # Create new phase for existing forage
                    try:
                        phase_std = PhaseStandard.objects.get(nomDePhase__startswith=normalize(rapport.nom_phase[0:2]))
                        Phase.objects.create(
                            idPhaseStandard=phase_std,
                            idForage=forage,
                            delaiActuel=1,
                            depthActuel=depth,
                            dateDebut=date_rapport,
                            coutActuel=cout_actuel,
                            coutCumulatifActuel=coutCumul_actuel,
                            currentOperation=current_operation,
                            plannedOperation=planned_operation
                        )
                    except PhaseStandard.DoesNotExist:
                        print(f"PhaseStandard not found for {rapport.nom_phase[0:2]}")
            else:
                # Create new phase for new forage
                try:
                    phase_std = PhaseStandard.objects.get(nomDePhase__startswith=phase_actuelle[0:2])
                    Phase.objects.create(
                        idPhaseStandard=phase_std,
                        idForage=forage,
                        delaiActuel=1,
                        coutActuel=cout_actuel,
                        dateDebut=date_rapport,
                        depthActuel=depth,
                        coutCumulatifActuel=coutCumul_actuel,
                        currentOperation=current_operation,
                        plannedOperation=planned_operation
                    )
                except PhaseStandard.DoesNotExist:
                    print(f"PhaseStandard not found for {phase_actuelle[0:2]}")
            
            # Create notifications for responsible users
            # Modified to match your Notification model structure without 'message' field
            responsables = User.objects.filter(role='responsable')
            for user in responsables:
                Notification.objects.create(
                    iduser=user,
                    idRapport=rapport,
                    dateNotif=timezone.now().date(),
                    analysed=False
                    # 'message' field removed as it's not in your model
                )
                
        except Exception as e:
            print(f"Error processing imported rapport: {str(e)}")
            import traceback
            traceback.print_exc()